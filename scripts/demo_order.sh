#!/usr/bin/env bash
# Places a sample order through the gateway and lists all orders. Used to prove persistence.
BASE="${BASE:-http://localhost}"      # set BASE=http://localhost:8081 if you changed GATEWAY_PORT
echo "--- products (first 2)"; curl -s "$BASE/api/products" | head -c 300; echo
echo "--- placing order"
curl -s -X POST "$BASE/api/orders" -H 'Content-Type: application/json' \
  -d '{"customer":"Demo User","address":"1 Test Street","items":[{"product_id":1,"qty":2},{"product_id":3,"qty":1}]}'; echo
echo "--- all orders"; curl -s "$BASE/api/orders"; echo
