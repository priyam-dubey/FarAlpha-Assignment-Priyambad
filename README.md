# Flask and MongoDB Deployment on Kubernetes

## 1. Project Overview

This project demonstrates deploying a Flask REST API connected to MongoDB using Kubernetes and Minikube.

I implemented containerization, persistent database storage, MongoDB authentication, Kubernetes configuration management (ConfigMap and Secret), resource requests and limits, and CPU-based Horizontal Pod Autoscaling (HPA).

### Architecture

```
 Your computer (Windows)
        |
        |  minikube service flask-service --url
        v
 +---------------------- Minikube cluster ----------------------------+
 |                                                                    |
 |  flask-service (NodePort 30080 -> 5000)                            |
 |        |                                                           |
 |        v                                                           |
 |  flask-app Deployment: 2 to 5 Pods (scaled by the HPA)             |
 |        |   connects to host "mongodb-service" (Kubernetes DNS)     |
 |        v                                                           |
 |  mongodb-service (ClusterIP 27017, internal only)                  |
 |        |                                                           |
 |        v                                                           |
 |  mongodb StatefulSet: Pod mongodb-0 (authentication enabled)       |
 |        |   mounts /data/db                                         |
 |        v                                                           |
 |  mongodb-pvc (1Gi)  --bound to-->  mongodb-pv (hostPath)           |
 +--------------------------------------------------------------------+
```

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Python and Flask | REST API |
| MongoDB 7.0 | Database |
| PyMongo | MongoDB connectivity |
| Docker | Containerization |
| Kubernetes | Container orchestration |
| Minikube | Local Kubernetes cluster |
| kubectl | Kubernetes management |
| Metrics Server | Supplies CPU/memory usage to the HPA |
| Docker Hub | Container image registry |

## 3. Repository Structure

```
flask-mongodb-k8s/
├── app/
│   ├── app.py                  Flask application
│   └── requirements.txt        Flask 3.0.3, pymongo 4.8.0
├── k8s/
│   ├── app-configmap.yaml      ConfigMap (MongoDB host and port)
│   ├── mongodb-secret.yaml     Secret (MongoDB username and password)
│   ├── mongodb-pv.yaml         PersistentVolume (1Gi)
│   ├── mongodb-pvc.yaml        PersistentVolumeClaim (1Gi)
│   ├── mongodb-statefulset.yaml  MongoDB StatefulSet
│   ├── mongodb-service.yaml    MongoDB Service (ClusterIP)
│   ├── flask-deployment.yaml   Flask Deployment (2 replicas)
│   ├── flask-service.yaml      Flask Service (NodePort)
│   └── flask-hpa.yaml          Horizontal Pod Autoscaler
├── docs/testing-evidence/      Screenshots used in this README
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .env.example                Example variables for local runs only
└── README.md
```

> **Where to run commands:** unless a step says otherwise, run every command in **Windows PowerShell** from the project root:
> `C:\Assignment\FarAlpha Assignment Priyambad\flask-mongodb-k8s`

## 4. How Each Part Works

### 4.1 Flask application (`app/app.py`)

| Endpoint | Method | What it does |
|---|---|---|
| `/` | GET | Returns `Welcome to the Flask app! The current time is: <Date and Time>` |
| `/data` | POST | Inserts the JSON object from the request body into MongoDB (returns `201`). Returns `400` if the body is not a non-empty JSON object. |
| `/data` | GET | Returns all stored documents as JSON, without the `_id` field (returns `200`). |

If MongoDB cannot be reached, `/data` returns a `503` JSON error instead of crashing.

### 4.2 MongoDB authentication and how Flask connects securely

- **MongoDB side:** the StatefulSet sets `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` from the Kubernetes Secret `mongodb-secret`. When the official `mongo` image starts with an empty data directory, it creates this root user and turns authentication on.
- **Flask side:** `app.py` reads `MONGODB_HOST` and `MONGODB_PORT` (from the ConfigMap) and `MONGODB_USERNAME` and `MONGODB_PASSWORD` (from the same Secret) and builds the connection string `mongodb://<user>:<password>@<host>:<port>/?authSource=admin`. Special characters in the password are escaped with `quote_plus`.
- No password is written in `app.py`, the Dockerfile or the Deployment. They are injected as environment variables at runtime.
- **Important:** `MONGO_INITDB_*` only takes effect the **first time** MongoDB starts with an empty data directory. Changing the Secret later does **not** change the password inside an existing database. See [Security notes](#9-security-notes).

### 4.3 ConfigMap and Secret

| Resource | File | Purpose | Contents |
|---|---|---|---|
| ConfigMap `flask-config` | `k8s/app-configmap.yaml` | Non-sensitive settings | `MONGODB_HOST=mongodb-service`, `MONGODB_PORT=27017` |
| Secret `mongodb-secret` | `k8s/mongodb-secret.yaml` | Sensitive credentials | `username`, `password` (values are never shown in this README) |

Both are consumed as environment variables (`configMapKeyRef` and `secretKeyRef`) by the Flask Deployment. The MongoDB StatefulSet uses the Secret only.

### 4.4 Persistent storage (PV and PVC)

- `mongodb-pv`: 1Gi, `ReadWriteOnce`, `storageClassName: manual`, reclaim policy `Retain`, backed by a `hostPath` at `/data/mongodb` on the Minikube node.
- `mongodb-pvc`: requests 1Gi with the same `storageClassName` and is bound directly to `mongodb-pv` (`volumeName: mongodb-pv`).
- The StatefulSet mounts the PVC at `/data/db`, which is where MongoDB stores its data.
- Result: if the MongoDB Pod is deleted and recreated, the new Pod mounts the same volume and the data is still there.
- Limitation: `hostPath` lives inside the Minikube virtual machine or container. Data survives Pod deletion and `minikube stop`/`start`, but is **lost on `minikube delete`**.

### 4.5 Services

| Service | Type | Port | Why this type |
|---|---|---|---|
| `flask-service` | NodePort | 5000 (nodePort 30080) | Makes Flask reachable from my computer through Minikube. |
| `mongodb-service` | ClusterIP | 27017 | Reachable only inside the cluster, so the database is never exposed outside. |

### 4.6 DNS resolution inside the cluster

Kubernetes runs a DNS server (CoreDNS). Every Service automatically gets a DNS name:

```
<service-name>.<namespace>.svc.cluster.local
```

For this project the full name is `mongodb-service.default.svc.cluster.local`. Pods in the same namespace can use just the short name `mongodb-service`.

How the Flask Pod reaches MongoDB:

1. The ConfigMap sets `MONGODB_HOST=mongodb-service`.
2. Flask opens a connection to `mongodb-service:27017`.
3. Inside the Pod, `/etc/resolv.conf` points at CoreDNS and contains search domains (such as `default.svc.cluster.local`), so the short name is expanded to the full name.
4. CoreDNS returns the Service's stable ClusterIP.
5. Traffic to that ClusterIP is routed by `kube-proxy` to a healthy Pod selected by the label `app: mongodb`.

Pod IPs change whenever a Pod is recreated, but the Service name and ClusterIP stay the same, so Flask never needs to know the MongoDB Pod's IP.

To check DNS from inside a running Flask Pod:

```powershell
kubectl exec deploy/flask-app -- python -c "import socket; print(socket.gethostbyname('mongodb-service'))"
```

It should print the ClusterIP shown by `kubectl get svc mongodb-service`.

### 4.7 Resource requests and limits

| Container | CPU request | Memory request | CPU limit | Memory limit |
|---|---|---|---|---|
| Flask (`flask-deployment.yaml`) | 200m | 250Mi | 500m | 500Mi |
| MongoDB (`mongodb-statefulset.yaml`) | 200m | 250Mi | 500m | 500Mi |

(`200m` = 0.2 CPU core. These values were read directly from the YAML files. The assignment lists the memory as `250M` and `500M`; the manifests use `Mi` units, which are slightly larger: 250Mi is about 262M.)

- **Request** = the amount Kubernetes *reserves*. The scheduler only places a Pod on a node that has this much free. The HPA also measures CPU usage as a percentage of the request.
- **Limit** = the maximum a container may use. Using more CPU than the limit makes the container *throttled* (slowed down). Using more memory than the limit makes the container get *OOMKilled* (stopped and restarted).
- Why both matter: requests give each Pod a guaranteed share, and limits stop one misbehaving Pod from starving the rest of the node.

### 4.8 Horizontal Pod Autoscaler (HPA) and Metrics Server

`k8s/flask-hpa.yaml` (`autoscaling/v2`) targets the `flask-app` Deployment:

- Minimum replicas: **2**
- Maximum replicas: **5**
- Metric: CPU, target average utilization **70%** of the CPU request. With a 200m request, scaling starts when average usage per Pod goes above about 140m.

The HPA needs the **Metrics Server** to read Pod CPU usage. It is not defined in the `k8s/` folder; on Minikube it is provided as an add-on (see Step 11). Without it, `kubectl get hpa` shows `<unknown>` for the CPU value.

### 4.9 Dockerfile explained

```dockerfile
FROM python:3.12-slim          # small official Python image
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1   # no .pyc files; logs appear immediately
WORKDIR /app                   # working folder inside the image
COPY app/requirements.txt .    # copy dependency list first so Docker can cache this layer
RUN pip install --no-cache-dir -r requirements.txt
COPY app/app.py .              # copy the application code
EXPOSE 5000                    # the port Flask listens on
CMD ["python", "app.py"]       # start the app
```

`.dockerignore` keeps `venv/`, `.env`, `.git/`, `k8s/`, `docs/` and `README.md` out of the build.

## 5. How I Completed the Assessment

### Step 1: Created the Flask Application

First, I created a Flask application with three REST API endpoints:

- `GET /` – Returns a welcome message and current application time.
- `POST /data` – Inserts JSON data into MongoDB.
- `GET /data` – Retrieves stored data from MongoDB.

I used PyMongo to connect Flask with MongoDB, and updated the code to authenticate with a username and password taken from environment variables (see section 4.2).

*Part 1 bonus question – why use a virtual environment?* A virtual environment gives each project its own copy of Python packages. This prevents version conflicts between projects, keeps the system Python clean, and makes the exact dependencies reproducible through `requirements.txt`.

### Step 2: Built the Docker Image

Next, I created a Dockerfile using Python 3.12 slim, installed the required dependencies, and built the application image.

**Run from:** the project root (the folder containing `Dockerfile`). The final `.` tells Docker to use the current folder as the build context.

```powershell
docker build -t flask-mongodb-app:v1 .
```

### Step 3: Pushed the Docker Image to Docker Hub

I logged in to Docker Hub, tagged the image with my Docker Hub username, and pushed it to the registry.

```powershell
docker login
docker tag flask-mongodb-app:v1 priyambaddubey/flask-mongodb-app:v1
docker push priyambaddubey/flask-mongodb-app:v1
```

- `docker login` signs in to Docker Hub.
- `docker tag` gives the local image a registry name (`username/image:tag`).
- `docker push` uploads it.

Anyone can download the image with:

```powershell
docker pull priyambaddubey/flask-mongodb-app:v1
```

**Docker Hub Image:** `priyambaddubey/flask-mongodb-app:v1`

![Docker Hub Image Push](docs/testing-evidence/docker-image-deployment.png)

### Step 4: Created the Minikube Kubernetes Cluster

I started Minikube using the Docker driver (Docker Desktop must be running first).

```powershell
minikube start --driver=docker --cpus=2 --memory=2048
kubectl get nodes
```

`kubectl get nodes` should show one node with status `Ready`.

I then created Kubernetes configuration files for the Flask Deployment, MongoDB StatefulSet, Services, ConfigMap, Secret, PersistentVolume, PersistentVolumeClaim, and HPA (see section 3 for the file list).

### Step 5: Deployed the Kubernetes Resources

**Before deploying:**

1. Make sure `image:` in `k8s/flask-deployment.yaml` points to the Docker Hub image `priyambaddubey/flask-mongodb-app:v1` (the file may contain a `YOUR_DOCKERHUB_USERNAME` placeholder).
2. Create the MongoDB Secret from the command line, choosing your own strong password, so that no real password is stored in a file that is committed to Git:

```powershell
kubectl create secret generic mongodb-secret --from-literal=username=admin --from-literal=password='<choose-a-strong-password>'
```

Then apply every manifest **except** the Secret file (so that the Secret you just created is not overwritten):

```powershell
Get-ChildItem .\k8s\*.yaml | Where-Object { $_.Name -ne 'mongodb-secret.yaml' } | ForEach-Object { kubectl apply -f $_.FullName }
```

I configured the Flask Deployment to use the Docker Hub image and verified the rollout.

```powershell
kubectl rollout status deployment/flask-app
```

![Docker Image Deployment and Rollout](docs/testing-evidence/04-docker-image-deployment-rollout.png)

### Step 6: Configured MongoDB Persistent Storage

I created a 1Gi PersistentVolume and PersistentVolumeClaim with `ReadWriteOnce` access.

I mounted the PVC at `/data/db` in the MongoDB StatefulSet.

I verified the storage configuration. Both should show `Bound`.

```powershell
kubectl get pv,pvc
```

![Persistent Volume and Persistent Volume Claim](docs/testing-evidence/06-pv-pvc-status.png)

### Step 7: Verified Kubernetes Pods and Services

I checked the Flask and MongoDB Pods and verified their Services.

```powershell
kubectl get pods
kubectl get svc
```

The Flask application used a NodePort Service, and MongoDB used an internal ClusterIP Service. Expected: two `flask-app-...` Pods and `mongodb-0`, all `Running` and `1/1` ready.

![Kubernetes Pods and Services](docs/testing-evidence/07-kubernetes-pods-services.png)

### Step 8: Accessed the Flask Application

I exposed the Flask application through the NodePort Service and generated a local Minikube URL.

```powershell
minikube service flask-service --url
```

With the Docker driver on Windows, this command prints a URL such as `http://127.0.0.1:<port>` and **must stay running**. Leave this PowerShell window open and use a second window for other commands. The port changes whenever Minikube restarts, so always re-run the command rather than reusing an old URL.

![Flask Application Access](docs/testing-evidence/01-flask-application-access-url.png)

### Step 9: Tested Flask API and MongoDB

I tested the Flask welcome endpoint, inserted sample JSON data into MongoDB, and retrieved the stored data.

In a second PowerShell window (replace the URL with your current one):

```powershell
$url = "http://127.0.0.1:<port>"
Invoke-RestMethod -Uri "$url/"
Invoke-RestMethod -Uri "$url/data" -Method Post -ContentType "application/json" -Body '{"sampleKey":"sampleValue"}'
Invoke-RestMethod -Uri "$url/data"
```

Expected: the welcome message, `status: Data inserted`, then a list containing `sampleKey = sampleValue`.

![Flask API and MongoDB Data Test](docs/testing-evidence/08-flask-api-test.png)

### Step 10: Verified MongoDB Persistence

I inserted data, deleted the MongoDB Pod, and waited for the StatefulSet to recreate it.

```powershell
kubectl delete pod mongodb-0
kubectl get pods -w        # wait until mongodb-0 is Running and 1/1, then press Ctrl+C
Invoke-RestMethod -Uri "$url/data"
```

I retrieved the previously inserted data again to verify that it remained available after Pod recreation.

![MongoDB Persistence Test](docs/testing-evidence/09-mongodb-persistence-test.png)

### Step 11: Configured Metrics Server and HPA

I verified the Metrics Server and configured HPA with a minimum of 2 replicas, a maximum of 5 replicas, and a CPU utilization target of 70%.

If the Metrics Server is not already running, enable it with Minikube's add-on:

```powershell
minikube addons enable metrics-server
```

```powershell
kubectl get deployment metrics-server -n kube-system
kubectl apply -f k8s/flask-hpa.yaml
kubectl get hpa
kubectl top pods
```

`kubectl top pods` shows live CPU and memory per Pod; `kubectl get hpa` should show a CPU percentage (not `<unknown>`) after about a minute.

![Metrics Server and HPA Setup](docs/testing-evidence/02-metrics-server-hpa-setup.png)

### Step 12: Generated Load for Autoscaling

I started eight PowerShell background jobs to continuously send HTTP requests to the Flask application and generate CPU load.

Example load generator (keep `minikube service flask-service --url` running in another window):

```powershell
$url = "http://127.0.0.1:<port>"
1..8 | ForEach-Object {
  Start-Job -ArgumentList $url -ScriptBlock {
    param($u)
    while ($true) { try { Invoke-WebRequest -Uri $u -UseBasicParsing | Out-Null } catch {} }
  }
}
```

Watch the autoscaler in another window:

```powershell
kubectl get hpa -w
```

I stopped and removed the jobs after the test.

```powershell
Get-Job | Stop-Job
Get-Job | Remove-Job
```

![HPA Load Generation Test](docs/testing-evidence/05-hpa-load-generation-test.png)

### Step 13: Verified HPA Scale-Up and Scale-Down

During the load test, CPU utilization increased to 96%, and HPA scaled the Flask replicas from 2 to 3.

After stopping the load generator, CPU utilization decreased to 0%, and HPA scaled the replicas back from 3 to 2. (By default Kubernetes waits about 5 minutes of low usage before scaling down, to avoid flapping.)

![HPA Autoscaling Test](docs/testing-evidence/03-hpa-autoscaling-test.png)

![HPA Scale-Up and Scale-Down](docs/testing-evidence/03-hpa-scale-up-and-scale-down.png)

## 6. Cleanup

Remove the application resources (keeps Minikube running):

```powershell
kubectl delete -f .\k8s\flask-hpa.yaml
kubectl delete -f .\k8s\flask-service.yaml
kubectl delete -f .\k8s\flask-deployment.yaml
kubectl delete -f .\k8s\mongodb-service.yaml
kubectl delete -f .\k8s\mongodb-statefulset.yaml
kubectl delete -f .\k8s\mongodb-pvc.yaml
kubectl delete -f .\k8s\mongodb-pv.yaml
kubectl delete -f .\k8s\app-configmap.yaml
kubectl delete secret mongodb-secret
```

Stop the cluster (keeps data), or delete it completely (**deletes the MongoDB data**):

```powershell
minikube stop
minikube delete
```

## 7. Design Choices and Alternatives

| Choice | Why | Alternative considered |
|---|---|---|
| **StatefulSet** for MongoDB | Gives the database a stable Pod name and storage, which suits stateful workloads. | A Deployment is simpler but is meant for stateless Pods. |
| **ClusterIP** Service for MongoDB | The database should be reachable only inside the cluster. | NodePort/LoadBalancer would expose the database outside the cluster, which is unnecessary and unsafe. |
| **NodePort** Service for Flask | Simple way to reach the app from my computer on Minikube. | LoadBalancer (needs `minikube tunnel`) or Ingress (extra component); both add complexity not required here. |
| **hostPath PV + PVC** | Simple and works on any local Minikube; matches the assignment's PV/PVC requirement. | A dynamically provisioned PVC via the default StorageClass would need no manual PV; `hostPath` is not suitable for multi-node production clusters. |
| **Secret** for credentials, **ConfigMap** for host/port | Keeps passwords out of the image and code, and separates sensitive from non-sensitive settings. | Hard-coding values in the Deployment (insecure) or in the image (insecure). |
| **`MONGO_INITDB_ROOT_*` variables** to enable authentication | The official MongoDB image creates the root user and enables auth on first start. | A custom init script or a dedicated least-privilege application user. |
| **CPU-based HPA at 70%** | Required by the assignment; CPU is supported directly by Metrics Server. | Custom or memory metrics would need extra setup. |
| **Same requests/limits on both workloads** | Matches the sample values in the assignment (0.2 CPU/250M request, 0.5 CPU/500M limit). | Tuning separately per workload after measuring real usage. |
| **Python 3.12 slim base image** | Small image and fast builds. | Full `python:3.12` image is much larger. |

## 8. Problems Encountered and How I Resolved Them

| Problem | Resolution |
|---|---|
| Minikube service URL changed after restarts. | Re-run `minikube service flask-service --url` each session and use the URL it prints; keep that window open. |
| Git was first initialised in the wrong (parent) folder and the wrong contents were pushed. | I removed the incorrect local `.git` folder and worked from the actual project folder. |
| `git push` was rejected because GitHub had commits I did not have locally, then `git pull` reported a conflict in `README.md`. | I inspected the state and resolved it before pushing (never with a force-push). |
| A Kubernetes Secret manifest was committed to the public repository. | Treated the credential as compromised. Required actions are listed in section 9 (rotation inside MongoDB, removal from tracked files and history). <!-- AUTHOR: confirm rotation is done before submitting, then tick/describe it here --> |

## 9. Security Notes

- Real credentials must never be committed. `k8s/mongodb-secret.yaml` must contain **placeholders only** in any public repository; create the real Secret with `kubectl create secret ...` (Step 5).
- Add `k8s/mongodb-secret.yaml` to `.gitignore` and keep a sanitized copy such as `k8s/mongodb-secret.example.yaml` for reference.
- A password that was ever pushed to a public repository is compromised even after the file is deleted, because it remains in Git history. Rotate it.
- **Rotating the password:** editing the Kubernetes Secret alone is **not enough**, because MongoDB only reads `MONGO_INITDB_ROOT_PASSWORD` the first time it initialises an empty data directory. Change the password inside MongoDB itself (for example with `db.changeUserPassword` in `mongosh`), then update the Secret to match and restart the Flask Pods (`kubectl rollout restart deployment/flask-app`).
- `.env` is excluded by `.gitignore` and `.dockerignore`; `.env.example` is for local development only.

## 10. Final Results

- Flask REST API connected successfully to MongoDB with authentication.
- Docker image pushed to Docker Hub.
- Kubernetes Deployment and MongoDB StatefulSet deployed.
- Persistent storage configured and tested.
- Flask (NodePort) and MongoDB (ClusterIP) Services configured.
- ConfigMap and Secret configured.
- Resource requests and limits configured for both Flask and MongoDB.
- Metrics Server and HPA configured (min 2, max 5, 70% CPU).
- HPA scaled Flask replicas from 2 to 3 and back to 2.
- MongoDB data remained available after Pod recreation.

### Known limitations

- `hostPath` storage is for local/single-node use only and is lost on `minikube delete`.
- MongoDB runs as a single replica (no replica set or high availability).
- Flask connects with the MongoDB root user; a dedicated least-privilege user would be better in production.
- The MongoDB Service is a regular ClusterIP Service, not a headless Service, so individual Pod DNS names (such as `mongodb-0.mongodb-service`) are not available. This does not affect the application, which connects through `mongodb-service`.