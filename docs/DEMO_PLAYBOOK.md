# Live Presentation Demo Playbook — Highly Available API Gateway

This document is your exact step-by-step guide for presenting and demonstrating the **High Availability (HA) & Self-Healing Web Architecture** on AWS.

---

## Architecture Summary (Demo Edition)

- **Compute**: Single EC2 instance in an Auto Scaling Group (min=1, max=2) spanning 2 Availability Zones.
- **Load Balancer**: Multi-AZ AWS Application Load Balancer (ALB) performing `/healthz` HTTP health checks every 15s.
- **Shared State**: Managed AWS ElastiCache Redis cluster in private subnets. Rate limit counters survive instance replacement.
- **Local Database**: PostgreSQL container on EC2. Auto-migrated and seeded on instance launch (`python manage.py seed_demo_data`).
- **Observability**:
  - **AWS CloudWatch**: Native dashboard, alarms on unhealthy hosts, 5xx errors, and high CPU, with SNS email alerting.
  - **Prometheus + Grafana**: Live containerized dashboard on ports `9090` and `3000` for application-level rate limiting metrics.

---

## 1. Pre-Demo Setup (30–45 Mins Before Presentation)

### Step 1: Configure Variables
Copy the example config and populate your AWS details:
```bash
cd /home/ayush/Desktop/APIGateway/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
- `demo_ssh_cidr`: Your public IP address with `/32` (get it via `curl -s ifconfig.me`).
- `key_pair_name`: An existing AWS EC2 key pair name in `us-east-1`.
- `alert_email`: Your email address to receive SNS alarm notifications.
- `domain_name`: Leave blank `""` to use the ALB DNS directly, or enter a domain if using Route 53.

### Step 2: Deploy the Stack
```bash
./scripts/deploy.sh
```
*Note: Provisioning takes ~8–10 minutes (primarily waiting for ElastiCache).*

### Step 3: Verify & Collect Endpoints
```bash
terraform output
```
Note down:
- `alb_url`: e.g. `http://apigateway-alb-xxxx.us-east-1.elb.amazonaws.com`
- `cloudwatch_dashboard`: URL to open in AWS Console
- Check health:
  ```bash
  curl -s $(terraform output -raw alb_url)/healthz | jq .
  ```

### Step 4: Confirm SNS Email
Check your email inbox and click **"Confirm subscription"** on the AWS Notification email.

### Step 5: Extract Generated Demo API Keys
SSH into the EC2 instance using the IP from the AWS Console:
```bash
ssh -i ~/.ssh/<your-key>.pem ec2-user@<instance-public-ip>
sudo cat /var/log/user-data.log | grep -A 5 "DEMO API KEYS"
exit
```
Keep the generated `demo-free` API key handy on your clipboard.

### Step 6: Prepare Browser Tabs
1. **Tab 1**: ALB Health Check: `http://<ALB-DNS>/healthz`
2. **Tab 2**: AWS Console → EC2 → Target Groups → Target Health
3. **Tab 3**: AWS Console → CloudWatch Dashboard
4. **Tab 4**: Grafana Dashboard: `http://<instance-public-ip>:3000`
5. **Tab 5**: Terminal with SSH / curl commands ready

---

## 2. Presentation Flow (30 Minutes)

```
[1. Architecture Tour] ──> [2. Rate Limiting Demo] ──> [3. 💀 KILL INSTANCE]
         │                                                        │
         ▼                                                        ▼
[7. Teardown (IaC)] <── [6. CloudWatch Alert] <── [5. State Survived] <── [4. Watch Self-Healing]
```

---

### Scene 1: Architecture Overview (5 mins)
- **Show**: AWS Console (VPC with 2 public & 2 private subnets, ALB, ASG, ElastiCache cluster).
- **Key Talking Point**:
  > *"Every component you see here — networking, compute, caching, monitoring, and security boundaries — was provisioned via Terraform with zero manual clicking. The entire stack is codified, repeatable, and designed to operate within AWS Free Tier limits."*

---

### Scene 2: Live Traffic & Distributed Rate Limiting (5 mins)
- **Action**: Run a burst test from your local terminal against the ALB URL:
  ```bash
  ALB_URL="http://<ALB_DNS>"
  API_KEY="<YOUR_DEMO_FREE_KEY>"

  for i in $(seq 1 15); do
    curl -s -o /dev/null -w "Req $i: HTTP %{http_code}\n" -H "X-API-Key: $API_KEY" $ALB_URL/api/users/1
  done
  ```
- **Show**:
  - Terminal outputs HTTP 200 for the first allowed requests, then HTTP 429 once the token bucket / limit is exhausted.
  - Grafana dashboard showing `gateway_rate_limit_decisions_total` incrementing.
- **Key Talking Point**:
  > *"Rate limits are enforced atomically via Lua scripts running inside AWS ElastiCache Redis, not in memory on the application server. This ensures consistency across any number of gateway nodes."*

---

### Scene 3: The Failure Injection — Kill the Instance (1 min)
- **Action**: SSH into the active EC2 instance and simulate a critical kernel or container failure:
  ```bash
  ssh -i ~/.ssh/<your-key>.pem ec2-user@<instance-public-ip>
  sudo systemctl stop docker
  exit
  ```
- **Key Talking Point**:
  > *"I have just abruptly killed the Docker daemon. The gateway application, Nginx proxy, Postgres, and monitoring agents are all dead. No humans have been notified yet. Watch the automated recovery."*

---

### Scene 4: Watch Self-Healing in Real Time (5 mins)
- **Action**: Switch between Target Group health and CloudWatch.
  1. ALB health check fails 3 consecutive intervals (`/healthz` times out / returns connection refused).
  2. Target Group status shifts from `healthy` to `unhealthy`.
  3. CloudWatch alarm `apigateway-unhealthy-hosts` triggers.
  4. Auto Scaling Group terminates the unhealthy instance and launches a replacement instance in an alternate subnet.
  5. The replacement EC2 instance runs `user_data.sh`, pulls code, launches the production containers, migrates Postgres, and connects to the existing ElastiCache Redis.
  6. Target status transitions back to `healthy`.
  7. Run:
     ```bash
     curl -s $ALB_URL/healthz | jq .
     ```
     Response returns HTTP 200: `{"status": "ok", "checks": {"database": true, "redis": true}}`.
- **Key Talking Point**:
  > *"The failure was detected at the load balancer level, an alarm was published, and the Auto Scaling Group restored the desired capacity without human intervention."*

---

### Scene 5: Verified Shared State Continuity (3 mins)
- **Action**: Send requests with the original API key:
  ```bash
  curl -s -H "X-API-Key: $API_KEY" -w "\nStatus: %{http_code}\n" $ALB_URL/api/users/1
  ```
- **Key Talking Point**:
  > *"The instance is completely new, yet the application works and the rate-limiting tier state in ElastiCache persisted seamlessly across the compute lifecycle."*

---

### Scene 6: Observability & Alerting Confirmation (3 mins)
- **Show**:
  - The SNS alert email received: `ALARM: apigateway-unhealthy-hosts`.
  - The subsequent `OK: apigateway-unhealthy-hosts` email received when the new instance recovered.
  - CloudWatch Alarm history tab showing exact state transitions.

---

### Scene 7: Full Infrastructure Teardown (2 mins)
- **Action**:
  ```bash
  ./scripts/teardown.sh
  ```
- **Key Talking Point**:
  > *"With a single command, Terraform destroys all provisioned resources in reverse dependency order. Zero lingering compute, zero ongoing costs."*
