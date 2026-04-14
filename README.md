# Arc Store

A demo e-commerce store with a React frontend, Spring Boot backend, and a Python load generator.

## Project layout

```
arc-store/
├── backend/          Spring Boot 3.2 + H2
├── frontend/         React (Vite) + nginx
├── load-generator/   Python script
├── k8s/              Kubernetes manifests (namespace: arc-store)
└── build.sh          Build all Docker images
```

## Dependencies

The backend calls the tax-service at the URL configured by the `TAX_SERVICE_URL` environment variable.

- Local development fallback: `http://localhost:8081`
- Kubernetes deployment (configured in `k8s/configmap.yaml`): `http://tax-service.tax-service.svc.cluster.local:8081`

The tax-service is a separate repo deployed in its own Kubernetes namespace, but reachable from this app through the in-cluster DNS service URL above.

## Build Docker images

Run from the `arc-store/` directory:

```bash
./build.sh
```

This builds all three images for `linux/amd64` and `linux/arm64` using `docker buildx`.

## Deploy to Kubernetes

```bash
kubectl apply -f k8s/
```

Wait for pods to be ready:

```bash
kubectl get pods -n arc-store -w
```

## Access locally

```bash
# Store UI
nohup kubectl port-forward svc/arc-frontend 3000:80 -n arc-store > /tmp/arc-frontend-port-forward.log 2>&1 &

# Backend API (direct)
nohup kubectl port-forward svc/arc-backend 8080:8080 -n arc-store > /tmp/arc-backend-port-forward.log 2>&1 &
```

Open http://localhost:3000

## Local development (no Docker)

Start the tax-service first (see its own repo), then:

**Backend:**
```bash
cd backend
mvnw spring-boot:run
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

The frontend dev server will be available at http://localhost:5173/

**Load generator:**
```bash
cd load-generator
pip install -r requirements.txt
python generator.py
```

## Watch load generator logs

```bash
kubectl logs -f deployment/arc-load-generator -n arc-store
```

## API

| Method | Path          | Body                                      | Description       |
|--------|---------------|-------------------------------------------|-------------------|
| GET    | /api/products | —                                         | List all products |
| POST   | /api/orders   | `{ productId, quantity, shippingState }`  | Place an order    |
