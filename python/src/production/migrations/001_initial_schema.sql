-- BeeAI Production Database Schema
-- Version: 1.0
-- Date: 2026-05-05

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Validation Runs Table
CREATE TABLE IF NOT EXISTS validation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    target_host VARCHAR(253) NOT NULL,
    credential_id VARCHAR(100) NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 0 AND score <= 100),
    status VARCHAR(50) NOT NULL,
    workflow_status VARCHAR(50) NOT NULL,
    execution_time_seconds DECIMAL(10, 3) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for validation_runs
CREATE INDEX idx_validation_runs_user_created ON validation_runs(user_id, created_at DESC);
CREATE INDEX idx_validation_runs_target_host ON validation_runs(target_host);
CREATE INDEX idx_validation_runs_status ON validation_runs(status);
CREATE INDEX idx_validation_runs_score ON validation_runs(score);
CREATE INDEX idx_validation_runs_session ON validation_runs(session_id);

-- Validation Checks Table
CREATE TABLE IF NOT EXISTS validation_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES validation_runs(id) ON DELETE CASCADE,
    check_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    message TEXT,
    expected TEXT,
    actual TEXT,
    severity VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for validation_checks
CREATE INDEX idx_validation_checks_run_id ON validation_checks(run_id);
CREATE INDEX idx_validation_checks_status ON validation_checks(status);
CREATE INDEX idx_validation_checks_severity ON validation_checks(severity);

-- Discovery Results Table
CREATE TABLE IF NOT EXISTS discovery_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES validation_runs(id) ON DELETE CASCADE,
    application_name VARCHAR(255) NOT NULL,
    confidence INTEGER NOT NULL,
    evidence JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for discovery_results
CREATE INDEX idx_discovery_results_run_id ON discovery_results(run_id);
CREATE INDEX idx_discovery_results_app_name ON discovery_results(application_name);

-- Evaluation Results Table
CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES validation_runs(id) ON DELETE CASCADE,
    overall_health VARCHAR(50) NOT NULL,
    confidence DECIMAL(5, 4) NOT NULL,
    critical_issues JSONB,
    recommendations JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for evaluation_results
CREATE INDEX idx_evaluation_results_run_id ON evaluation_results(run_id);
CREATE INDEX idx_evaluation_results_health ON evaluation_results(overall_health);

-- User Sessions Table
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Indexes for user_sessions
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX idx_user_sessions_last_activity ON user_sessions(last_activity);

-- Audit Log Table
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for audit_log
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);

-- Users Table (for authentication)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    permissions JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Indexes for users
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_validation_runs_updated_at BEFORE UPDATE ON validation_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views for common queries

-- Recent validations view
CREATE OR REPLACE VIEW recent_validations AS
SELECT 
    vr.id,
    vr.user_id,
    vr.target_host,
    vr.score,
    vr.status,
    vr.workflow_status,
    vr.execution_time_seconds,
    vr.created_at,
    COUNT(vc.id) FILTER (WHERE vc.status = 'PASS') as passed_checks,
    COUNT(vc.id) FILTER (WHERE vc.status = 'FAIL') as failed_checks,
    COUNT(vc.id) FILTER (WHERE vc.status = 'WARN') as warning_checks
FROM validation_runs vr
LEFT JOIN validation_checks vc ON vr.id = vc.run_id
GROUP BY vr.id
ORDER BY vr.created_at DESC;

-- User statistics view
CREATE OR REPLACE VIEW user_statistics AS
SELECT 
    user_id,
    COUNT(*) as total_validations,
    AVG(score) as average_score,
    MAX(score) as max_score,
    MIN(score) as min_score,
    COUNT(*) FILTER (WHERE workflow_status = 'completed') as successful_validations,
    COUNT(*) FILTER (WHERE workflow_status = 'failed') as failed_validations,
    MAX(created_at) as last_validation
FROM validation_runs
GROUP BY user_id;

-- Comments for documentation
COMMENT ON TABLE validation_runs IS 'Main table storing validation execution records';
COMMENT ON TABLE validation_checks IS 'Individual check results for each validation run';
COMMENT ON TABLE discovery_results IS 'Application discovery results from validation runs';
COMMENT ON TABLE evaluation_results IS 'Health assessment and evaluation results';
COMMENT ON TABLE user_sessions IS 'Active user session tracking';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for all user actions';
COMMENT ON TABLE users IS 'User accounts for authentication and authorization';

-- Grant permissions (adjust as needed for your environment)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO beeai_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO beeai_app;

-- Initial data (optional)
-- INSERT INTO users (username, email, hashed_password, role, permissions) VALUES
-- ('admin', 'admin@example.com', '$2b$12$...', 'admin', '["validation:execute", "validation:view", "admin:manage"]');

COMMIT;

-- Made with Bob
