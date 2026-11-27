# agl-daily-dashboards

Hosted, read-only Xero access for AGL Group (Butlers Catering and Butlers Point of Sale Logistics) plus the daily 16:45 finance dashboards sent by WhatsApp.

Status: stage 1 (Xero access, per-company tokens on a persistent volume). Stages 2 to 4 (report builder, WhatsApp sender and scheduler, secured connectors) follow.

Rules: Xero is only ever read (GET). No accounting record, payment or approval is created or changed.

Railway variables: XERO_CLIENT_ID, XERO_CLIENT_SECRET, XERO_SEED_BCS, XERO_SEED_BPOS, INTERNAL_KEY, TOKEN_DIR=/data. Mount a volume at /data.
