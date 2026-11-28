#!/usr/bin/env bash
# =========================================================
# MT Multimarcas — instala o Conector de WhatsApp numa VPS Ubuntu
# Uso (como root):
#   curl -fsSL https://mt-multimarcas-catalogo.netlify.app/instalar/instalar.sh | bash -s -- SEU_TOKEN
# Opcional: um domínio próprio já apontado para a VPS como 2º argumento.
# =========================================================
set -euo pipefail

TOKEN="${1:-}"
SITE="https://mt-multimarcas-catalogo.netlify.app"
BASE="$SITE/instalar"
DIR="/opt/mt-conector"

if [ "$(id -u)" -ne 0 ]; then echo "Rode como root (ou com sudo)."; exit 1; fi
if [ "${#TOKEN}" -lt 20 ]; then echo "Informe o token do conector (o comando completo está no chat)."; exit 1; fi

echo "==> Atualizando o sistema e instalando o básico"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl ca-certificates gnupg debian-keyring debian-archive-keyring apt-transport-https

echo "==> Instalando Node.js 22"
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

echo "==> Instalando Caddy (HTTPS automático)"
if ! command -v caddy >/dev/null 2>&1; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy
fi

echo "==> Baixando o conector"
id mtcrm >/dev/null 2>&1 || useradd --system --home "$DIR" --shell /usr/sbin/nologin mtcrm
mkdir -p "$DIR"
curl -fsSL "$BASE/conector.mjs" -o "$DIR/conector.mjs"
curl -fsSL "$BASE/package.json" -o "$DIR/package.json"
cd "$DIR"
npm install --omit=dev --no-audit --no-fund

cat > "$DIR/.env" <<EOF
CONECTOR_TOKEN=$TOKEN
SITE_URL=$SITE
PORTA=3000
EOF
chmod 600 "$DIR/.env"
chown -R mtcrm:mtcrm "$DIR"

echo "==> Criando o serviço (liga sozinho e reinicia se cair)"
cat > /etc/systemd/system/mt-conector.service <<EOF
[Unit]
Description=MT Multimarcas - Conector WhatsApp
After=network-online.target
Wants=network-online.target

[Service]
User=mtcrm
WorkingDirectory=$DIR
EnvironmentFile=$DIR/.env
ExecStart=/usr/bin/node $DIR/conector.mjs
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now mt-conector
systemctl restart mt-conector

echo "==> Configurando o endereço com HTTPS"
IP="$(curl -4 -fsS https://api.ipify.org || hostname -I | awk '{print $1}')"
DOMINIO="${2:-$(echo "$IP" | tr . -).sslip.io}"
cat > /etc/caddy/Caddyfile <<EOF
$DOMINIO {
  reverse_proxy 127.0.0.1:3000
}
EOF
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  ufw allow 80/tcp; ufw allow 443/tcp
fi
systemctl enable caddy
systemctl reload caddy || systemctl restart caddy

sleep 3
echo
echo "========================================================"
echo " Pronto! Conector instalado."
echo " Endereço do conector:  https://$DOMINIO"
echo " Mande esse endereço no chat para ligar no CRM."
echo " Ver o funcionamento:   journalctl -u mt-conector -f"
echo "========================================================"
