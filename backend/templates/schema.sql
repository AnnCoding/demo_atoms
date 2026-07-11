-- ===== 建表模板(PostgreSQL,按需复制 / 改名 / 加列)=====
-- 在 Supabase / psql / 任意 Postgres 客户端执行即可。

-- ① 通用记录表:uuid 主键 + jsonb 扩展字段 + 时间戳 + 软删除
CREATE TABLE IF NOT EXISTS records (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  data        jsonb,                       -- 灵活扩展(任意键值)
  amount      numeric(12,2) DEFAULT 0,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now(),
  deleted     boolean DEFAULT false
);
CREATE INDEX IF NOT EXISTS records_created_at_idx ON records (created_at DESC);
CREATE INDEX IF NOT EXISTS records_data_gin       ON records USING gin (data);

-- ② 自动维护 updated_at(复制到任意需要的表)
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS records_set_updated_at ON records;
CREATE TRIGGER records_set_updated_at BEFORE UPDATE ON records
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ③ 用户表(若用 Supabase Auth 可省略,直接用 auth.users;否则自建)
CREATE TABLE IF NOT EXISTS users (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email       text UNIQUE,
  name        text,
  created_at  timestamptz DEFAULT now()
);

-- ④ 关联表示例(外键)
CREATE TABLE IF NOT EXISTS user_records (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid REFERENCES users(id) ON DELETE CASCADE,
  record_id   uuid REFERENCES records(id) ON DELETE CASCADE,
  created_at  timestamptz DEFAULT now()
);
