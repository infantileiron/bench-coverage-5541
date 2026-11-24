首次启动按 `src/models/entities.py` 定义创建表，保留数据卷升级时先编写迁移。

## 复点抽样功能新增表

新增 `audit_sampling_plans`（抽样批次：锁定实见快照、分层抽签结果、整批推算结果）
与 `audit_recount_returns`（样本段现场回传及对账状态）。

- 全新数据库：应用启动时 `Base.metadata.create_all` 自动建表，无需手工迁移。
- 已有数据卷（MySQL 8.0）升级：`create_all` 不会修改既有表，但会创建上述两张新表；
  如组织流程要求显式迁移，可执行等价 DDL：

```sql
CREATE TABLE audit_sampling_plans (
  id INT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(100) NOT NULL,
  campaign VARCHAR(32) NOT NULL,
  status VARCHAR(16) NOT NULL,
  seed INT NOT NULL,
  confidence FLOAT NOT NULL,
  locked_snapshot JSON NOT NULL,
  strata JSON NOT NULL,
  result JSON NULL,
  author_id INT NOT NULL REFERENCES users(id),
  note TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_audit_sampling_plans_campaign (campaign),
  INDEX ix_audit_sampling_plans_status (status)
);

CREATE TABLE audit_recount_returns (
  id INT PRIMARY KEY AUTO_INCREMENT,
  plan_id INT NOT NULL REFERENCES audit_sampling_plans(id),
  segment_code VARCHAR(32) NOT NULL REFERENCES segments(code),
  state VARCHAR(12) NOT NULL,
  total_found INT NULL,
  asset_codes JSON NOT NULL,
  missing_locked JSON NOT NULL,
  reason TEXT NOT NULL,
  reporter VARCHAR(120) NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_recount_segment (plan_id, segment_code),
  INDEX ix_audit_recount_returns_plan_id (plan_id),
  INDEX ix_audit_recount_returns_state (state)
);
```
