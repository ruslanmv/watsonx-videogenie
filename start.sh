# ────────────────────────────────────────────────────────────────
# 1 · Clone the repo
git clone https://github.com/videogenie/watsonx-videogenie.git
cd watsonx-videogenie

# ────────────────────────────────────────────────────────────────
# 2 · (Cloud)  Provision shared IBM Cloud infrastructure
#     ► Skip this step entirely if you’re *only* hacking locally.
cd infra/terraform
terraform init
terraform apply -auto-approve -var domain="videogenie.cloud"
cd ../..

# ────────────────────────────────────────────────────────────────
# 3 · Build local OCI images (no push required for Kind)
make container-build TAG=$(git rev-parse --short HEAD)

# ────────────────────────────────────────────────────────────────
# 4 · Create Python toolchain
make setup
# If you want to run scripts manually:
source .venv/bin/activate

# ────────────────────────────────────────────────────────────────
# 5 · Create .env with your App ID + watsonx creds
cp .env.example .env
$EDITOR .env

# ────────────────────────────────────────────────────────────────
# 6 · Spin Kind cluster *for local smoke tests*
make kind-up          # → creates `videogenie` Kind cluster

# ────────────────────────────────────────────────────────────────
# 7 · Install mesh add‑ons inside Kind
make install-istio install-argo install-keda

# ────────────────────────────────────────────────────────────────
# 8 · Deploy the umbrella Helm chart into Kind
helm upgrade --install videogenie charts/videogenie \
  --namespace videogenie --create-namespace \
  --set global.image.tag=$(git rev-parse --short HEAD)

# ────────────────────────────────────────────────────────────────
# 9 · Run the front‑end dev server
cd frontend
npm ci
npm start            # ⇢ http://localhost:5173 (auto‑reload)

echo
echo "✅  Local stack is up."
echo "🖥  Front‑end: http://localhost:5173"
echo "💬  Avatar API: http://localhost:8000/avatars  (Kind NodePort)"