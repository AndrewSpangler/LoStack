#!/usr/bin/env bash
set -euo pipefail

CERTS_DIR="./certs"
mkdir -p "$CERTS_DIR"

# Ask user for domain
read -rp "Enter domain (e.g. example.com): " DOMAIN

# Generate Root CA (only once)
if [[ ! -f "$CERTS_DIR/rootCA.pem" || ! -f "$CERTS_DIR/rootCA-key.pem" ]]; then
  echo "Generating root CA..."
  openssl req -x509 -newkey rsa:2048 \
    -keyout "$CERTS_DIR/rootCA-key.pem" \
    -out "$CERTS_DIR/rootCA.pem" \
    -days 3650 -nodes \
    -subj "/CN=LoStack Development CA"
else
  echo "Root CA already exists, skipping..."
fi

# --- Function to generate certs ---
generate_cert() {
  local CN="$1"
  local FILE_PREFIX="$2"
  shift 2
  local DNS_ENTRIES=("$@")

  local CONFIG_FILE="$CERTS_DIR/openssl-${FILE_PREFIX}-san.cnf"

  # Build config with SANs
  cat > "${CONFIG_FILE}" <<EOF
[ req ]
default_bits       = 2048
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt             = no

[ req_distinguished_name ]
CN = ${CN}

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
$(for i in "${!DNS_ENTRIES[@]}"; do echo "DNS.$((i+1)) = ${DNS_ENTRIES[$i]}"; done)
EOF

  # Generate key + CSR
  openssl req -new -nodes \
    -newkey rsa:2048 \
    -keyout "$CERTS_DIR/${FILE_PREFIX}-key.pem" \
    -out "$CERTS_DIR/${FILE_PREFIX}.csr" \
    -config "${CONFIG_FILE}"

  # Sign with root CA
  openssl x509 -req \
    -in "$CERTS_DIR/${FILE_PREFIX}.csr" \
    -CA "$CERTS_DIR/rootCA.pem" -CAkey "$CERTS_DIR/rootCA-key.pem" -CAcreateserial \
    -out "$CERTS_DIR/${FILE_PREFIX}.pem" -days 365 \
    -extfile "${CONFIG_FILE}" -extensions req_ext

  rm "$CERTS_DIR/${FILE_PREFIX}.csr" "${CONFIG_FILE}"
}

# Generate domain cert
echo "Generating certificate for ${DOMAIN}..."
generate_cert "${DOMAIN}" "${DOMAIN}" "${DOMAIN}"

# Generate wildcard cert
echo "Generating wildcard certificate for *.${DOMAIN}..."
generate_cert "*.${DOMAIN}" "_wildcard.${DOMAIN}" "*.${DOMAIN}" "${DOMAIN}"

echo "Done!"
echo "Created files:"
ls -1 "$CERTS_DIR/${DOMAIN}-key.pem" \
      "$CERTS_DIR/${DOMAIN}.pem" \
      "$CERTS_DIR/_wildcard.${DOMAIN}-key.pem" \
      "$CERTS_DIR/_wildcard.${DOMAIN}.pem"
