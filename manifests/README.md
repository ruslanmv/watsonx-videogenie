# Manifests for Runtime Integration

This directory contains the Kubernetes manifests that serve as the critical runtime "glue" for the VideoGenie stack. These files configure the interaction between KEDA (for autoscaling), Kafka (for messaging), and Istio (for network routing), enabling a fully automated, event-driven architecture.

-----

## 1\. KEDA Autoscaling (`keda-scaledobject.yaml`)

This manifest defines a `ScaledObject`, a custom resource from the KEDA project, which provides intelligent, event-driven autoscaling for the GPU renderers.

  * **Event Source:** It is configured to monitor the `videoJob` topic in Kafka.
  * **Scaling Trigger:** It continuously checks the consumer group lag. If the number of unprocessed messages exceeds a threshold of **5**, it triggers a scale-up event.
  * **Target Deployment:** It manages the `renderer-deployment`, scaling the number of GPU-powered renderer pods horizontally.
  * **Scaling Rules:**
      * **Scale to Zero:** The number of replicas can scale down to **0** when there are no pending jobs, ensuring that expensive GPU resources are not consumed when idle.
      * **Max Replicas:** It can scale up to a maximum of **10** replicas to handle high loads.
      * **Polling & Cooldown:** It checks for new messages every **30 seconds** (`pollingInterval`) and waits for **5 minutes** (`cooldownPeriod`) of inactivity before scaling down to zero.
  * **Advanced HPA:** The configuration limits the rate of scaling to prevent unstable fluctuations, ensuring that the number of replicas at most doubles once per minute.

-----

## 2\. WebSocket Service (`websocket.yaml`)

This manifest bundles all the necessary resources to run and expose the real-time notification service.

  * **`Deployment`:** Deploys a lightweight WebSocket server (written in Node.js or Go). Its sole purpose is to "fan-out" status updates from the Argo rendering workflow to the correct front-end clients.
  * **`Service`:** Creates a stable internal DNS name for the WebSocket deployment within the cluster, allowing other services to discover it reliably.
  * **`Istio VirtualService`:** Securely exposes the WebSocket server on the public gateway. It routes traffic from the `/ws` path (e.g., `wss://videogenie.example.com/ws?jobId=...`) to the internal WebSocket service.
  * **High Availability:** The deployment runs with two replicas, and Istio manages the traffic, ensuring the service remains available even during updates or pod failures.

-----

## 🚀 How to Apply

Apply these manifests to your cluster using `kubectl`.

```bash
# Apply the KEDA autoscaler for the GPU renderers
kubectl apply -f manifests/keda-scaledobject.yaml

# Deploy the WebSocket service and expose it via Istio
kubectl apply -f manifests/websocket.yaml
```

-----

## ⚙️ End-to-End Workflow

With these two manifests in place, the following automated workflow is enabled:

1.  A user submits a "create video" request, which results in a message being published to the `videoJob` Kafka topic.
2.  KEDA detects the growing message lag in the topic.
3.  KEDA automatically scales up the `renderer-deployment` from 0 to N pods to handle the workload.
4.  Argo Workflows picks up the jobs and begins the GPU rendering process.
5.  Simultaneously, the user's browser maintains a WebSocket connection to the fan-out server.
6.  As Argo progresses through the rendering steps, it emits status events, which are forwarded through the WebSocket server to the browser, providing real-time progress updates without polling the main REST API.