#!/usr/bin/env bash
# Local quick-start (minikube) for the demo. Requires docker, kubectl, minikube, helm.
set -euo pipefail
minikube start --cpus=4 --memory=6g && minikube addons enable ingress && minikube addons enable metrics-server
kubectl apply -f k8s/app/namespace.yaml -f k8s/app/configmap.yaml -f k8s/app/secret.yaml -f k8s/app/rbac.yaml
kubectl apply -f k8s/app/
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts && helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f k8s/monitoring/values-kube-prometheus-stack.yaml
kubectl apply -f k8s/monitoring/ -n taskmanager
kubectl apply -f k8s/logging/efk.yaml
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
echo "Then: kubectl apply -f argocd/application.yaml"
