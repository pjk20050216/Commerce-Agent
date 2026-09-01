UPDATE listing_products SET tenant_id = 'dev' WHERE tenant_id = 'default';
UPDATE listing_tasks SET tenant_id = 'dev' WHERE tenant_id = 'default';
UPDATE asset_packages SET tenant_id = 'dev' WHERE tenant_id = 'default';
UPDATE generated_assets SET tenant_id = 'dev' WHERE tenant_id = 'default';
UPDATE adapter_configs SET tenant_id = 'dev' WHERE tenant_id = 'default';
UPDATE task_results SET tenant_id = 'dev' WHERE tenant_id = 'default';
