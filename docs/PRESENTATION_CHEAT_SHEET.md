# 🎤 Live Presentation Cheat Sheet — Step-by-Step Guide

Keep this open during your presentation. Follow the numbered steps, copy-paste the exact commands, and use the bullet points for what to say.

---

## 📋 Before Your Presentation (10 Minutes Before)

### Step 0: Deploy the Stack
Open your terminal:
```bash
cd /home/ayush/Desktop/APIGateway/terraform
./scripts/deploy.sh
```
*Type `yes` when prompted. Takes ~8–10 mins.*

When finished, your terminal will print everything:
```
Outputs:
alb_url              = "http://apigateway-alb-xxxx.us-east-1.elb.amazonaws.com"
health_check         = "curl -s http://apigateway-alb-xxxx.us-east-1.elb.amazonaws.com/healthz | jq ."
cloudwatch_dashboard = "https://us-east-1.console.aws.amazon.com/cloudwatch/..."
teardown             = "terraform destroy -auto-approve"
```

### Pre-Presentation Checklist:
1. **Email Confirmation**: Open your email (`ayushsriva2598@gmail.com`) and click **"Confirm subscription"** on the AWS SNS email.
2. **Copy the Demo API Key**:
   In AWS Console → EC2 → Instances, find the running gateway instance IP, then run:
   ```bash
   ssh -i ~/.ssh/Api-gateway-demo.pem ec2-user@<INSTANCE_PUBLIC_IP> "sudo cat /var/log/user-data.log | grep demo-free"
   ```
   *Copy the raw key that looks like `demo-free  → <key>`.*
3. **Open 4 Browser Tabs**:
   - **Tab 1**: ALB Health Check: `http://<YOUR_ALB_URL>/healthz`
   - **Tab 2**: AWS Console → **Target Groups** (select `apigateway-tg` → click **Targets** tab)
   - **Tab 3**: AWS Console → **EC2 Instances**
   - **Tab 4**: CloudWatch Dashboard link (printed in terminal)

---

## 🎬 Presentation Flow (Follow in Order)

```
[1. Architecture] ──> [2. Rate Limiting] ──> [3. KILL IT] ──> [4. Self-Healing] ──> [5. State Check] ──> [6. Teardown]
```

---

### Step 1: Architecture Tour (2–3 Mins)
**What to Show**:
Open AWS Console showing the VPC subnets, ALB, and ElastiCache.

**What to Say**:
> - *"We designed a highly available, self-healing API Gateway architecture deployed entirely via Infrastructure as Code (Terraform) within AWS Free Tier limits."*
> - *"Traffic enters via a Multi-AZ Application Load Balancer."*
> - *"An Auto Scaling Group manages our compute across 2 Availability Zones."*
> - *"Rate-limiting state is decoupled from compute into AWS ElastiCache Redis — so our servers are completely stateless and disposable."*

---

### Step 2: Prove Normal Operation & Rate Limiting (3 Mins)
**What to Do**:
Set your variables in your terminal:
```bash
ALB="http://apigateway-alb-408374234.us-east-1.elb.amazonaws.com"
KEY="7bhS-7AGTTxNxuiP0fkoFu7jU_mIwVe6RYUZjKyzLds"
```

1. Check health:
```bash
curl -s $ALB/healthz | jq .
```
*(Returns: `{"status": "ok", "checks": {"database": true, "redis": true}}`)*

2. Send a burst of 15 requests to trigger the rate limiter:
```bash
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "Req $i: HTTP %{http_code}\n" -H "X-API-Key: $KEY" $ALB/api/users/1
done
```

**What the Audience Sees**:
- Initial requests are accepted through the gateway
- Following requests immediately return **`HTTP 429` (Rate Limited / Too Many Requests)**!

**What to Say**:
> - *"Notice the atomic rate limiting in action: the first 10 requests are allowed, and subsequent requests immediately return HTTP 429 Too Many Requests."*
> - *"This is enforced atomically in ElastiCache Redis using Lua scripts, not in local server memory."*

---

### Step 3: The Failure Injection — Kill the Server (1 Min)
**What to Say**:
> - *"Now, let's simulate a catastrophic failure. I am going to SSH into the active server and kill the entire container runtime."*

**What to Do**:
```bash
ssh -i ~/.ssh/Api-gateway-demo.pem ec2-user@54.166.105.141
sudo systemctl stop docker
exit
```

**What to Say**:
> - *"Docker is dead. Gateway, Nginx, and local Postgres are terminated. Let's step back and watch the architecture recover on its own."*

---

### Step 4: Watch Self-Healing Live (4–5 Mins)
**What to Show**:
Switch between **Tab 2 (Target Groups)** and **Tab 3 (EC2 Instances)**:

1. **Target Group**:
   - Within ~45 seconds, the target turns from **Healthy** (green) to **Unhealthy** (red).
2. **CloudWatch & Email**:
   - Show your email inbox: you will receive an automated alert from AWS SNS (`ALARM: apigateway-unhealthy-hosts`).
3. **EC2 Instances Tab**:
   - The dead EC2 instance enters `Terminating`.
   - A **new EC2 instance automatically launches** (often in the other Availability Zone!).
4. **Target Group Health Restored**:
   - Within ~2–3 minutes, the new instance boots, runs Docker, pulls code, and the health check goes from `Initial` back to **Healthy** (green)!
5. **Prove it in the terminal**:
```bash
curl -s $ALB/healthz | jq .
```
*(Returns `HTTP 200 OK`)*

**What to Say**:
> - *"Zero human intervention. The load balancer detected the failed health check, alerted CloudWatch, and the Auto Scaling Group replaced the dead node with a brand new instance."*

---

### Step 5: Prove Rate Limit State Survived (2 Mins)
**What to Do**:
Run another request with the same API key:
```bash
curl -s -H "X-API-Key: $KEY" -w "\nHTTP %{http_code}\n" $ALB/api/users/1
```

**What to Say**:
> - *"Notice our API key still works immediately. The compute was completely destroyed and replaced, but our rate-limiting state in ElastiCache survived seamlessly."*
> - *"This proves the core architectural principle: Compute is disposable; state is durable."*

---

### Step 6: One-Command Teardown (1 Min)
**What to Say**:
> - *"Because everything was built with Infrastructure as Code, we can completely destroy the entire infrastructure with a single command — zero lingering costs."*

**What to Do**:
```bash
./scripts/teardown.sh
```

---

## 💡 Quick Answers to Likely Questions

| Question | Your Answer |
|---|---|
| **Why not Multi-AZ for the database?** | *"Multi-AZ RDS is not free-tier eligible. To strictly maintain zero-cost demo compliance, we ran a stateless containerized setup where compute is disposable and critical rate-limiting state resides in free-tier ElastiCache."* |
| **How does rate limiting stay atomic across instances?** | *"Every rate limit check is executed as a single atomic Redis Lua script (`EVALSHA`). Even with 10 gateway instances behind the ALB, there are no race conditions or counter desyncs."* |
| **Why use an ALB with a single instance in ASG?** | *"The ALB provides health checking and multi-AZ failover capability. When the instance dies, the ASG can launch a replacement in either Availability Zone A or B without changing the client endpoint."* |
