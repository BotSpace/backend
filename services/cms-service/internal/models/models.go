package models

import "time"

// FieldType enumerates supported CMS field types.
type FieldType string

const (
	FieldTypeText     FieldType = "text"
	FieldTypeNumber   FieldType = "number"
	FieldTypeBoolean  FieldType = "boolean"
	FieldTypeDate     FieldType = "date"
	FieldTypeRelation FieldType = "relation"
	FieldTypeFile     FieldType = "file"
	FieldTypeEmail    FieldType = "email"
	FieldTypeURL      FieldType = "url"
)

// Collection represents a CMS collection stored in PostgreSQL metadata.
type Collection struct {
	ID        string    `bson:"_id,omitempty"      json:"id"`
	Name      string    `bson:"name"               json:"name"`
	UserID    string    `bson:"user_id"            json:"user_id"`
	ProjectID string    `bson:"project_id"         json:"project_id"`
	CreatedAt time.Time `bson:"created_at"         json:"created_at"`
	UpdatedAt time.Time `bson:"updated_at"         json:"updated_at"`
}

// Field defines a single column/field within a Collection.
type Field struct {
	ID                 string    `bson:"_id,omitempty"        json:"id"`
	CollectionID       string    `bson:"collection_id"        json:"collection_id"`
	Name               string    `bson:"name"                 json:"name"`
	Type               FieldType `bson:"type"                 json:"type"`
	Required           bool      `bson:"required"             json:"required"`
	Default            string    `bson:"default,omitempty"    json:"default,omitempty"`
	RelationCollection string    `bson:"relation_collection,omitempty" json:"relation_collection,omitempty"`
	CreatedAt          time.Time `bson:"created_at"           json:"created_at"`
	UpdatedAt          time.Time `bson:"updated_at"           json:"updated_at"`
}

// ExportTaskStatus enumerates possible export task states.
type ExportTaskStatus string

const (
	ExportStatusPending    ExportTaskStatus = "pending"
	ExportStatusProcessing ExportTaskStatus = "processing"
	ExportStatusCompleted  ExportTaskStatus = "completed"
	ExportStatusFailed     ExportTaskStatus = "failed"
)

// ExportTask tracks an asynchronous collection export.
type ExportTask struct {
	ID               string           `bson:"_id,omitempty"      json:"id"`
	CollectionID     string           `bson:"collection_id"      json:"collection_id"`
	Status           ExportTaskStatus `bson:"status"             json:"status"`
	FilePath         string           `bson:"file_path,omitempty" json:"file_path,omitempty"`
	ErrorMessage     string           `bson:"error_message,omitempty" json:"error_message,omitempty"`
	TotalRecords     int64            `bson:"total_records"      json:"total_records"`
	ProcessedRecords int64            `bson:"processed_records"  json:"processed_records"`
	CreatedAt        time.Time        `bson:"created_at"         json:"created_at"`
	UpdatedAt        time.Time        `bson:"updated_at"         json:"updated_at"`
}

// QueryRequest is the body sent to the /query endpoint.
type QueryRequest struct {
	Action string                 `json:"action" binding:"required"`
	Data   map[string]interface{} `json:"data"`
	Filter map[string]interface{} `json:"filter"`
	Limit  int64                  `json:"limit"`
	Skip   int64                  `json:"skip"`
}
