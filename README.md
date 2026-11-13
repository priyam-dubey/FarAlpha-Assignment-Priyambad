# Flask and MongoDB Deployment on Kubernetes

## 1. Project Overview

This project demonstrates how to deploy a Flask web application connected to MongoDB using Kubernetes.

The Flask application provides REST API endpoints to insert and retrieve data from MongoDB. The application runs inside Kubernetes Pods, while MongoDB runs as a StatefulSet with persistent storage.

The project also uses Kubernetes ConfigMaps and Secrets for configuration management, Services for communication, and Horizontal Pod Autoscaler (HPA) to automatically scale the Flask application based on CPU utilization.

The application was deployed and tested locally using Minikube. The Docker image was also pushed to Docker Hub so that it can be used by other Kubernetes environments.

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application programming language |
| Flask | Web application framework |
| MongoDB 7.0 | Database |
| PyMongo | Python library for MongoDB connectivity |
| Docker | Containerization |
| Kubernetes | Container orchestration |
| Minikube | Local Kubernetes cluster |
| kubectl | Kubernetes command-line tool |
| Docker Hub | Container image registry |

## 3. Project Architecture

The application follows this architecture:

```text
                  User / Client
                       |
                       |
                Flask Service
                  (NodePort)
                       |
                       |
                Flask Deployment
                 (2-5 Replicas)
                       |
                       |
                MongoDB Service
                  (ClusterIP)
                       |
                       |
                MongoDB StatefulSet
                    (1 Pod)
                       |
                       |
                Persistent Volume
                       |
                       |
                Persistent Storage
```

Additional Kubernetes resources:

- ConfigMap: Stores non-sensitive application configuration.
- Secret: Stores MongoDB authentication credentials.
- HPA: Automatically adjusts Flask replicas based on CPU utilization.
- Metrics Server: Provides resource metrics required by HPA.

## 4. Project Structure

```text
flask-mongodb-k8s/
│
├── app/
│   ├── app.py
│   └── requirements.txt
│
├── docs/
│   └── testing-evidence/
│       ├── README.md
│       └── screenshots/
│
├── k8s/
│   ├── app-configmap.yaml
│   ├── flask-deployment.yaml
│   ├── flask-hpa.yaml
│   ├── flask-service.yaml
│   ├── mongodb-pv.yaml
│   ├── mongodb-pvc.yaml
│   ├── mongodb-secret.yaml
│   ├── mongodb-service.yaml
│   └── mongodb-statefulset.yaml
│
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
└── README.md
```

## 5. Application Endpoints

The Flask application provides the following endpoints:

### GET /

Returns a welcome message and the current application time.

Example:

```http
GET /
```

### POST /data

Inserts a JSON document into MongoDB.

Example request:

```json
{
  "sampleKey": "sampleValue"
}
```

Successful response:

```json
{
  "status": "Data inserted"
}
```

### GET /data

Retrieves the documents stored in the MongoDB collection.

Example:

```http
GET /data
```

The application returns the stored documents in JSON format.

## 6. Docker Image

The application is packaged into a Docker image using the Dockerfile.

The Dockerfile uses Python 3.12 slim as its base image, installs the required Python dependencies, copies the Flask application, and starts the application on port 5000.

### Build the Docker image

Open PowerShell and navigate to the project root directory:

```powershell
cd "C:\Assignment\FarAlpha Assignment Priyambad\flask-mongodb-k8s"
```

Build the image:

```powershell
docker build -t flask-mongodb-app:v1 .
```

Verify the image:

```powershell
docker images flask-mongodb-app
```

## 7. Push the Docker Image to Docker Hub

The application image is available on Docker Hub.

**Docker Hub image:**

`priyambaddubey/flask-mongodb-app:v1`

To push an updated image, follow these steps from the project root directory in PowerShell.

### Step 1: Log in to Docker Hub

```powershell
docker login
```

Complete the browser authentication if requested.

### Step 2: Tag the image

```powershell
docker tag flask-mongodb-app:v1 priyambaddubey/flask-mongodb-app:v1
```

### Step 3: Push the image

```powershell
docker push priyambaddubey/flask-mongodb-app:v1
```

### Step 4: Update the Kubernetes Deployment

In `k8s/flask-deployment.yaml`, configure the container image as:

```yaml
image: priyambaddubey/flask-mongodb-app:v1
```

Apply the updated Deployment:

```powershell
kubectl apply -f .\k8s\flask-deployment.yaml
```

Check the Deployment rollout:

```powershell
kubectl rollout status deployment/flask-app
```

Verify the image configured in the Deployment:

```powershell
kubectl get deployment flask-app -o jsonpath="{.spec.template.spec.containers[0].image}"
```

The expected image is:

```text
priyambaddubey/flask-mongodb-app:v1
```

A locally built image can be loaded directly into Minikube for local development. Pushing the image to Docker Hub makes it available to Kubernetes environments that can access the registry.

## 8. Kubernetes Deployment Using Minikube

### Prerequisites

Install the following tools:

- Docker Desktop
- Minikube
- kubectl
- Python 3.8 or later (for local application development)

Make sure Docker Desktop is running before starting Minikube.

### Step 1: Start Minikube

Open PowerShell:

```powershell
minikube start --driver=docker --cpus=2 --memory=2048
```

Check the Kubernetes context:

```powershell
kubectl config current-context
```

The expected context is:

```text
minikube
```

### Step 2: Apply Kubernetes configuration files

Navigate to the project root directory:

```powershell
cd "C:\Assignment\FarAlpha Assignment Priyambad\flask-mongodb-k8s"
```

Apply all Kubernetes resources:

```powershell
kubectl apply -f .\k8s\
```

This applies the ConfigMap, Secret, PersistentVolume, PersistentVolumeClaim, MongoDB StatefulSet, Services, Flask Deployment, and HPA configuration.

### Step 3: Verify persistent storage

```powershell
kubectl get pv,pvc
```

The PersistentVolume and PersistentVolumeClaim should show the `Bound` status.

### Step 4: Verify MongoDB

```powershell
kubectl get statefulset
kubectl get pods
kubectl get svc
```

MongoDB should run as a StatefulSet with one Pod.

### Step 5: Verify Flask Deployment

```powershell
kubectl get deployment flask-app
kubectl get pods
```

The Flask Deployment should have two ready replicas under normal conditions.

### Step 6: Verify Metrics Server

Metrics Server is required for CPU-based autoscaling.

Enable the Minikube addon if it is not already enabled:

```powershell
minikube addons enable metrics-server
```

Check its status:

```powershell
kubectl get deployment metrics-server -n kube-system
```

Check resource metrics:

```powershell
kubectl top pods
```

### Step 7: Verify HPA

```powershell
kubectl get hpa
```

The HPA should show:

- Minimum replicas: 2
- Maximum replicas: 5
- CPU utilization target: 70%

### Step 8: Access the Flask application

Run:

```powershell
minikube service flask-service --url
```

This command provides a local URL for accessing the Flask application.

Keep the PowerShell window running while using the URL.

The URL can be used to test the application from another PowerShell window.

## 9. Kubernetes Services and DNS Resolution

Kubernetes Services provide stable network endpoints for communication between application components.

### Flask Service

The Flask application uses a NodePort Service to make the application accessible locally.

The configured NodePort is 30080.

### MongoDB Service

MongoDB uses a ClusterIP Service on port 27017.

This Service is accessible internally within the Kubernetes cluster and is not exposed through a public NodePort.

### Kubernetes DNS

Kubernetes provides an internal DNS service that allows Pods to communicate using Service names instead of manually configured IP addresses.

The Flask application connects to MongoDB using:

```text
mongodb-service
```

The MongoDB hostname is configured through the ConfigMap.

When Flask tries to connect to `mongodb-service`, Kubernetes DNS resolves the Service name to the corresponding internal Service IP.

This allows Flask Pods to communicate with MongoDB without depending on individual Pod IP addresses.

Using a ClusterIP Service also keeps MongoDB internal to the cluster.

## 10. MongoDB Authentication and Configuration

The project uses Kubernetes ConfigMap and Secret resources to manage application configuration.

### ConfigMap

The ConfigMap stores non-sensitive configuration values:

- MongoDB hostname
- MongoDB port

The Flask application reads these values through environment variables.

### Secret

The Kubernetes Secret stores MongoDB authentication credentials.

The Flask Deployment reads the credentials through environment variables instead of storing them directly in the application code.

MongoDB is configured with authentication, and the Flask application uses the credentials to connect to the database.

Actual credentials are not included in this README.

## 11. Persistent Storage

MongoDB uses a PersistentVolume and PersistentVolumeClaim to store database data.

The configured storage is:

| Property | Value |
|---|---|
| Storage capacity | 1Gi |
| Access mode | ReadWriteOnce |
| Reclaim policy | Retain |
| Storage class | manual |
| Storage type | hostPath |

The MongoDB StatefulSet mounts the PersistentVolumeClaim at:

```text
/data/db
```

This allows MongoDB data to remain available when its Pod is recreated.

### Persistence testing

The following test was performed:

1. Inserted sample data into MongoDB.
2. Deleted the MongoDB Pod.
3. Waited for the StatefulSet to recreate the Pod.
4. Retrieved the previously inserted data again.

The existing data was still available after Pod recreation.

This verified persistence across MongoDB Pod recreation in the local Minikube environment.

**Note:** The configured hostPath storage is local to Minikube. It should not be treated as a backup or as storage that survives deletion of the Minikube cluster.

## 12. Resource Requests and Limits

Kubernetes resource requests and limits are configured for both Flask and MongoDB containers.

| Resource | Request | Limit |
|---|---:|---:|
| CPU | 200m | 500m |
| Memory | 250Mi | 500Mi |

### Resource Requests

Requests specify the minimum resources Kubernetes uses when scheduling a container onto a node.

For example, a CPU request of 200m represents 0.2 CPU cores.

A memory request of 250Mi represents 250 mebibytes.

### Resource Limits

Limits define the maximum CPU and memory resources a container can use.

The configured limits are:

- CPU: 500m (0.5 CPU cores)
- Memory: 500Mi

CPU usage can be throttled when a container reaches its CPU limit. A container exceeding its memory limit may be terminated and restarted.

These values provide resource boundaries for the application and database containers.

## 13. Horizontal Pod Autoscaler (HPA)

The project uses Kubernetes Horizontal Pod Autoscaler to automatically adjust the number of Flask application replicas based on CPU utilization.

The HPA configuration is:

| Property | Value |
|---|---|
| Minimum replicas | 2 |
| Maximum replicas | 5 |
| CPU utilization target | 70% |
| Target Deployment | flask-app |

The CPU utilization target is calculated relative to the CPU request.

For the Flask container:

- CPU request = 200m
- CPU target = 70%
- Target CPU usage = approximately 140m per Pod

When average CPU utilization rises above the target, HPA can increase the number of Flask replicas.

When CPU utilization decreases, HPA can reduce the number of replicas, subject to its scaling behavior.

### HPA testing

A CPU load test was performed against the Flask application.

The following results were observed:

| Test stage | CPU utilization | Flask replicas |
|---|---:|---:|
| Initial state | 1% | 2 |
| Under load | 54% | 2 |
| High CPU load | 96% | 2 |
| Scale-up | 96% | 3 |
| Continued load | 72% | 3 |
| After stopping load | 0% | 2 |

The HPA successfully increased the Flask replicas from 2 to 3 when CPU utilization exceeded the configured target.

After the load generator was stopped, CPU utilization decreased and HPA automatically scaled the replicas back to 2.

MongoDB remained running during the test.

### Monitoring commands

Monitor HPA continuously:

```powershell
kubectl get hpa -w
```

Check Pods:

```powershell
kubectl get pods
```

Check resource utilization:

```powershell
kubectl top pods
```

## 14. API Testing

The application was tested through its Minikube Service URL.

Replace the example URL below with the URL returned by `minikube service flask-service --url`.

### Test the welcome endpoint

```powershell
Invoke-RestMethod http://127.0.0.1:58524/
```

The application returned a welcome message and the current time.

### Insert data into MongoDB

```powershell
$body = @{
    sampleKey = "sampleValue"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:58524/data" -Method Post -ContentType "application/json" -Body $body
```

The application returned:

```json
{
  "status": "Data inserted"
}
```

### Retrieve data from MongoDB

```powershell
Invoke-RestMethod http://127.0.0.1:58524/data
```

The previously inserted sample data was successfully returned:

```text
sampleKey
---------
sampleValue
```

## 15. Design Choices and Alternatives

### Deployment for Flask

A Kubernetes Deployment is used for Flask because the application is stateless and can run across multiple interchangeable replicas.

An alternative would be a StatefulSet, but Flask does not require stable Pod identities or persistent local storage.

### StatefulSet for MongoDB

A StatefulSet is used for MongoDB because it provides stable Pod identity and works with persistent storage.

A Deployment could also run a single database Pod, but StatefulSet is a suitable choice for this database setup.

### NodePort for Flask

NodePort provides a simple way to access Flask from outside the local Kubernetes cluster.

For larger production deployments, a LoadBalancer or Ingress could be used.

### ClusterIP for MongoDB

ClusterIP keeps MongoDB accessible within the Kubernetes cluster.

This avoids exposing the database directly outside the cluster.

### PersistentVolume and PersistentVolumeClaim

PV and PVC provide persistent storage for MongoDB.

The current setup uses hostPath storage through Minikube. In a cloud environment, a cloud-managed persistent disk would be a more suitable alternative.

### ConfigMap and Secret

ConfigMap stores non-sensitive settings, while Secret stores database credentials.

This separates configuration from application code.

Kubernetes Secrets provide a mechanism for handling sensitive configuration, but additional security controls such as encryption at rest and access restrictions are important in production.

### Horizontal Pod Autoscaler

HPA was selected to automatically scale Flask replicas based on CPU utilization instead of manually changing the replica count.

## 16. Troubleshooting

### Pods are not starting

Check Pod status:

```powershell
kubectl get pods
```

Inspect Pod events:

```powershell
kubectl describe pod <pod-name>
```

### MongoDB connection problems

Check MongoDB Pod:

```powershell
kubectl get pods
```

Check MongoDB Service:

```powershell
kubectl get svc mongodb-service
```

Check application logs:

```powershell
kubectl logs deployment/flask-app
```

### HPA metrics are unavailable

Check Metrics Server:

```powershell
kubectl get pods -n kube-system
```

Check resource metrics:

```powershell
kubectl top pods
```

### Deployment rollout problems

Check rollout status:

```powershell
kubectl rollout status deployment/flask-app
```

Inspect Deployment:

```powershell
kubectl describe deployment flask-app
```

## 17. Testing Evidence

Screenshots and additional testing evidence are maintained separately in:

`docs/testing-evidence/`

The evidence should include:

- Flask welcome endpoint response.
- MongoDB data insertion and retrieval.
- MongoDB persistence after Pod recreation.
- HPA scale-up from 2 to 3 replicas.
- HPA scale-down from 3 to 2 replicas.
- Docker Hub image push.
- Kubernetes Deployment using the Docker Hub image.

See [Testing Evidence](docs/testing-evidence/README.md) for the available screenshots and test records.

## 18. Conclusion

This project demonstrates the deployment of a Flask application connected to an authenticated MongoDB database using Kubernetes.

The application was successfully deployed on Minikube with multiple Flask replicas, persistent MongoDB storage, internal service communication, and CPU-based automatic scaling.

The Docker image was pushed to Docker Hub and the Kubernetes Deployment was updated to use the registry image.

The API endpoints, MongoDB persistence, and HPA scale-up and scale-down behavior were tested successfully.

The project provides practical experience with Docker, Kubernetes Deployments, StatefulSets, Services, ConfigMaps, Secrets, persistent storage, resource management, and autoscaling.