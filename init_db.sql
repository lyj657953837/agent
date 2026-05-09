

-- ======================================================================
-- 1. Data Management Layer
-- ======================================================================

CREATE TABLE IF NOT EXISTS uploaded_data (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    data_id         VARCHAR(64) NOT NULL UNIQUE,
    file_name       VARCHAR(512) NOT NULL,
    data_type       VARCHAR(32) NOT NULL COMMENT 'IMAGE/VIDEO/AUDIO/TEXT',
    storage_path    VARCHAR(1024) NOT NULL,
    metadata_extracted TEXT COMMENT 'JSON: MetadataExtracted',
    status          VARCHAR(32) NOT NULL DEFAULT 'PREPROCESSED',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_data_id (data_id),
    INDEX idx_data_type (data_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ======================================================================
-- 2. Sensor Data Layer
-- ======================================================================

CREATE TABLE IF NOT EXISTS sensor_data (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id       VARCHAR(64) NOT NULL,
    timestamp       BIGINT NOT NULL COMMENT 'Unix ms',
    gps_lat         DOUBLE,
    gps_lon         DOUBLE,
    gps_altitude    DOUBLE,
    imu_pitch       DOUBLE,
    imu_roll        DOUBLE,
    imu_yaw         DOUBLE,
    battery_level   INT,
    battery_voltage DOUBLE,
    battery_current DOUBLE,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_id (device_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ======================================================================
-- 3. Task Orchestration Layer
-- ======================================================================

CREATE TABLE IF NOT EXISTS analysis_tasks (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id         VARCHAR(64) NOT NULL UNIQUE,
    task_name       VARCHAR(256) NOT NULL,
    description     TEXT,
    data_ids        JSON COMMENT 'List of data IDs',
    constraints     JSON COMMENT 'TaskConstraints',
    status          VARCHAR(32) NOT NULL DEFAULT 'PLANNED',
    sub_tasks_json  JSON COMMENT 'List of SubTask',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS task_sub_tasks (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id         VARCHAR(64) NOT NULL,
    sub_task_id     VARCHAR(64) NOT NULL,
    assigned_agent  VARCHAR(64) NOT NULL,
    action          TEXT,
    dependence      JSON,
    status          VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    progress        FLOAT NOT NULL DEFAULT 0,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_sub_task_id (sub_task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ======================================================================
-- 4. Execution / Result Layer
-- ======================================================================

CREATE TABLE IF NOT EXISTS effect_results (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    result_id       VARCHAR(64) NOT NULL UNIQUE,
    task_id         VARCHAR(64) NOT NULL,
    coverage_json   JSON COMMENT 'CoverageAnalysis',
    accuracy_json   JSON COMMENT 'AccuracyAnalysis',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS report_results (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    result_id           VARCHAR(64) NOT NULL UNIQUE,
    task_id             VARCHAR(64) NOT NULL,
    coordinates_json    JSON COMMENT 'List of CoordinateItem',
    evidence_json       JSON COMMENT 'List of EvidenceItem',
    route_efficiency_json   JSON COMMENT 'RouteEfficiency',
    obstacle_energy_json    JSON COMMENT 'ObstacleAndEnergy',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS quality_results (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    result_id       VARCHAR(64) NOT NULL UNIQUE,
    task_id         VARCHAR(64) NOT NULL,
    total_score     FLOAT NOT NULL DEFAULT 0,
    dimensions_json JSON COMMENT 'Dict of DimensionScore',
    suggestions_json JSON COMMENT 'List of OptimizationSuggestion',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ======================================================================
-- 5. Validation Layer
-- ======================================================================

CREATE TABLE IF NOT EXISTS validation_results (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    validation_id   VARCHAR(64) NOT NULL UNIQUE,
    task_id         VARCHAR(64) NOT NULL,
    summary_json    JSON COMMENT 'ValidationSummary',
    details_json    JSON COMMENT 'List of ValidationDetail',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS anomaly_handling (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    handle_id           VARCHAR(64) NOT NULL UNIQUE,
    anomaly_ids         JSON COMMENT 'List of anomaly IDs',
    action              VARCHAR(64) NOT NULL DEFAULT 'MANUAL_INTERVENTION',
    handler_comment     TEXT,
    llm_recommendation  TEXT,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_handle_id (handle_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ======================================================================
-- 6. Output Layer
-- ======================================================================

CREATE TABLE IF NOT EXISTS export_jobs (
    id                      BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id                  VARCHAR(64) NOT NULL UNIQUE,
    task_id                 VARCHAR(64) NOT NULL,
    format                  VARCHAR(32) NOT NULL DEFAULT 'PDF',
    include_evidence_chain  BOOLEAN NOT NULL DEFAULT TRUE,
    include_validation_report BOOLEAN NOT NULL DEFAULT FALSE,
    status                  VARCHAR(32) NOT NULL DEFAULT 'PROCESSING',
    download_url            VARCHAR(1024),
    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_feedback (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    feedback_id         VARCHAR(64) NOT NULL UNIQUE,
    task_id             VARCHAR(64) NOT NULL,
    satisfaction_score  FLOAT NOT NULL,
    user_comment        TEXT,
    corrected_info      JSON,
    rag_sync_status     VARCHAR(32) NOT NULL DEFAULT 'QUEUED',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;