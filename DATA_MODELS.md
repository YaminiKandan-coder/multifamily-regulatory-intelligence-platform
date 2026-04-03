# Data Models

## Supabase Tables

| Table | Key Columns |
|---|---|
| `jurisdictions` | id, type (federal/state/county/city), name, parent_id, state_code, fips_code |
| `regulations` | id, jurisdiction_id, domain, category, source_name, url, content, content_hash, version, is_current, effective_date |
| `regulation_embeddings` | id, regulation_id, embedding vector(3072), chunk_text |
| `email_subscriptions` | id, email, jurisdiction_id, subscribed_at, is_active |
| `regulation_updates` | id, regulation_id, update_summary, affected_jurisdictions (JSONB), detected_at |
| `pet_policies` | id, jurisdiction_id, esa_deposit_allowed, service_animal_fee, breed_restrictions (JSONB), max_pet_deposit_amount, source_regulation_id |
| `insurance_requirements` | id, jurisdiction_id, landlord_can_require, min_liability_coverage, tenant_must_show_proof, notes, source_regulation_id |
| `app_settings` | key (PK), value, updated_at |
| `regulation_sources` | id, jurisdiction_id, source_name, url (unique), domain, category, state_code, is_active, last_scraped_at, last_error, created_at |
