# Testing Evidence

## 1. HPA Scale-Up Test

The CPU utilization increased to 96%, and HPA
scaled the Flask replicas from 2 to 3.

![HPA Scale-Up](screenshots/hpa-scale-up.png)

## 2. HPA Scale-Down Test

After stopping the load generator, CPU utilization
reduced and HPA scaled replicas from 3 to 2.

![HPA Scale-Down](screenshots/hpa-scale-down.png)

## 3. Docker Hub Deployment

The Kubernetes Deployment successfully used
the Docker Hub image.

![Docker Hub Deployment](screenshots/docker-hub-deployment.png)

## 4. Flask API Test

The Flask welcome endpoint and MongoDB data
retrieval were tested successfully.

![Flask API Test](screenshots/flask-api-test.png)

## 5. MongoDB Persistence Test

Previously inserted data remained available
after MongoDB Pod recreation.

![MongoDB Persistence](screenshots/mongodb-persistence.png)
