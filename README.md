<<<<<<< HEAD + feature branch
# End-to-End DevOps Pipeline for a Cloud-Native Task Manager (ENSP461 Capstone) - develop branch
=======
# End-to-End DevOps Pipeline for a Cloud-Native Task Manager (ENSP461 Capstone) - feature branch
>>>>>>> feature/api

Flask Task Manager (login, CRUD, REST API, Postgres) delivered by: **GitHub → Jenkins → SonarQube/Trivy → Docker → Argo CD (GitOps) → Kubernetes (Blue-Green) → Prometheus/Grafana + EFK**, with infra by **Terraform** and config by **Ansible**.

Replace placeholders first: `shivanii2507`, `shivxnii` (grep for them).

## Layout
| Path | Purpose |
|---|---|
| `app/`, `tests/` | Flask app + pytest suite (88% coverage) |
| `Dockerfile`, `docker-compose.yml` | Multi-stage non-root image; full local stack (app, Postgres, Prometheus, Grafana, cAdvisor; Jenkins/SonarQube via `--profile ci`) |
| `Jenkinsfile`, `sonar-project.properties` | CI: test → Sonar + quality gate → build → Trivy → push → GitOps commit |
| `k8s/app/` | Deployment (blue/green), Service, ConfigMap, Secret, PVC/StatefulSet, HPA, Ingress, RBAC, NetworkPolicy |
| `k8s/monitoring/`, `monitoring/` | kube-prometheus-stack values, ServiceMonitor, alerts; Compose Prometheus + Grafana dashboard |
| `k8s/logging/efk.yaml` | Elasticsearch + Kibana + Fluentd DaemonSet |
| `argocd/application.yaml` | GitOps app (auto-sync, self-heal, prune) |
| `ansible/` | Playbooks: Docker, Kubernetes (kubeadm), app deploy, base config/hardening |
| `terraform/` | AWS VPC + EC2 via modules, variables, outputs |
| `scripts/` | scale / rolling update / rollback demo, blue-green switch, minikube bootstrap |

## Run steps
**1. Local (Docker Compose)**
```bash
cp .env.example .env            # edit passwords
docker compose up -d --build    # app :5000, Prometheus :9090, Grafana :3000 (admin/GRAFANA_PASSWORD), cAdvisor :8080
pip install -r requirements-dev.txt && pytest --cov=app
```
**2. CI** – `docker compose --profile ci up -d jenkins sonarqube`. In Jenkins add credentials `dockerhub-creds`, `github-creds`, Sonar server `sonarqube` (token as secret text); create a Pipeline-from-SCM job; add GitHub webhook `http://<jenkins>:8081/github-webhook/` so every push triggers a build.

**3. Infra (optional cloud)**
```bash
cd terraform && cp terraform.tfvars.example terraform.tfvars && terraform init && terraform apply
cd ../ansible && ansible-galaxy collection install -r requirements.yml
# put terraform output IP into inventory.ini
ansible-playbook site.yml
```
**4. Kubernetes (local alternative: `scripts/bootstrap-cluster.sh` on minikube)**
```bash
kubectl apply -f k8s/app/                      # or let Argo CD do it: kubectl apply -f argocd/application.yaml
kubectl -n taskmanager port-forward svc/taskmanager 8080:80
./scripts/demo-k8s.sh shivanii2507/taskmanager:1.0.1   # scaling, rolling update, rollback
./scripts/switch-color.sh green                # blue-green cut-over (rollback: ... blue)
```
**5. Monitoring / Logging** – Grafana dashboard "Task Manager - Overview" (CPU, memory, container health, request rate, p95 latency). Kibana: NodePort 30601, create data view `logstash-*`.

## Security
SonarQube quality gate, Trivy image scan, non-root/read-only-rootfs containers, K8s Secrets (use Sealed Secrets in prod), Jenkins Credentials store, RBAC Roles (viewer/deployer), NetworkPolicy for DB, UFW + fail2ban via Ansible.

## Validation status
Unit tests, YAML/JSON and Ansible syntax were validated. Terraform/Kubernetes/Jenkins runs must be executed in your environment to capture screenshots.
