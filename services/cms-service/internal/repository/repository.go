package repository

import (
	"context"
	"fmt"
	"time"

	"github.com/botspace/cms-service/internal/models"
	"github.com/google/uuid"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

const (
	colCollections = "collections"
	colFields      = "fields"
	colExportTasks = "export_tasks"
)

// CMSRepository provides all MongoDB operations for the CMS service.
type CMSRepository struct {
	db *mongo.Database
}

// New creates a new CMSRepository backed by the given database.
func New(db *mongo.Database) *CMSRepository {
	return &CMSRepository{db: db}
}

// ---- Collections ----

// CreateCollection inserts a new collection document.
func (r *CMSRepository) CreateCollection(ctx context.Context, c *models.Collection) error {
	c.ID = uuid.New().String()
	c.CreatedAt = time.Now().UTC()
	c.UpdatedAt = time.Now().UTC()
	_, err := r.db.Collection(colCollections).InsertOne(ctx, c)
	return err
}

// GetCollectionByID retrieves a collection by its ID.
func (r *CMSRepository) GetCollectionByID(ctx context.Context, id string) (*models.Collection, error) {
	var c models.Collection
	err := r.db.Collection(colCollections).FindOne(ctx, bson.M{"_id": id}).Decode(&c)
	if err != nil {
		return nil, err
	}
	return &c, nil
}

// GetCollectionByName retrieves a collection by project and name.
func (r *CMSRepository) GetCollectionByName(ctx context.Context, projectID, name string) (*models.Collection, error) {
	var c models.Collection
	err := r.db.Collection(colCollections).FindOne(ctx, bson.M{
		"project_id": projectID,
		"name":       name,
	}).Decode(&c)
	if err != nil {
		return nil, err
	}
	return &c, nil
}

// ListCollections returns all collections for a given project.
func (r *CMSRepository) ListCollections(ctx context.Context, projectID string) ([]models.Collection, error) {
	cursor, err := r.db.Collection(colCollections).Find(ctx, bson.M{"project_id": projectID})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var result []models.Collection
	if err := cursor.All(ctx, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// UpdateCollection updates the name of an existing collection.
func (r *CMSRepository) UpdateCollection(ctx context.Context, id string, update bson.M) error {
	update["updated_at"] = time.Now().UTC()
	_, err := r.db.Collection(colCollections).UpdateOne(
		ctx,
		bson.M{"_id": id},
		bson.M{"$set": update},
	)
	return err
}

// DeleteCollection removes a collection document.
func (r *CMSRepository) DeleteCollection(ctx context.Context, id string) error {
	_, err := r.db.Collection(colCollections).DeleteOne(ctx, bson.M{"_id": id})
	return err
}

// ---- Fields ----

// CreateField inserts a new field document.
func (r *CMSRepository) CreateField(ctx context.Context, f *models.Field) error {
	f.ID = uuid.New().String()
	f.CreatedAt = time.Now().UTC()
	f.UpdatedAt = time.Now().UTC()
	_, err := r.db.Collection(colFields).InsertOne(ctx, f)
	return err
}

// ListFields returns all fields belonging to a collection.
func (r *CMSRepository) ListFields(ctx context.Context, collectionID string) ([]models.Field, error) {
	cursor, err := r.db.Collection(colFields).Find(ctx, bson.M{"collection_id": collectionID})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var result []models.Field
	if err := cursor.All(ctx, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// DeleteFieldsByCollection removes all fields for a collection.
func (r *CMSRepository) DeleteFieldsByCollection(ctx context.Context, collectionID string) error {
	_, err := r.db.Collection(colFields).DeleteMany(ctx, bson.M{"collection_id": collectionID})
	return err
}

// ---- Data (per-project, per-collection) ----

// dataCollection returns the mongo collection used to store actual CMS records.
// Each project gets its own collection namespace: project_{projectID}_{collectionName}.
func (r *CMSRepository) dataCollection(projectID, collectionName string) *mongo.Collection {
	name := fmt.Sprintf("data_%s_%s", projectID, collectionName)
	return r.db.Collection(name)
}

// InsertData inserts a single document into the project/collection data store.
func (r *CMSRepository) InsertData(ctx context.Context, projectID, collectionName string, doc map[string]interface{}) (interface{}, error) {
	doc["_id"] = uuid.New().String()
	doc["created_at"] = time.Now().UTC()
	doc["updated_at"] = time.Now().UTC()
	res, err := r.dataCollection(projectID, collectionName).InsertOne(ctx, doc)
	if err != nil {
		return nil, err
	}
	return res.InsertedID, nil
}

// FindData queries documents with an optional filter, limit, and skip.
func (r *CMSRepository) FindData(ctx context.Context, projectID, collectionName string, filter map[string]interface{}, limit, skip int64) ([]map[string]interface{}, error) {
	opts := options.Find()
	if limit > 0 {
		opts.SetLimit(limit)
	}
	if skip > 0 {
		opts.SetSkip(skip)
	}

	if filter == nil {
		filter = map[string]interface{}{}
	}

	cursor, err := r.dataCollection(projectID, collectionName).Find(ctx, filter, opts)
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var result []map[string]interface{}
	if err := cursor.All(ctx, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// FindOneData returns a single document matching the filter.
func (r *CMSRepository) FindOneData(ctx context.Context, projectID, collectionName string, filter map[string]interface{}) (map[string]interface{}, error) {
	if filter == nil {
		filter = map[string]interface{}{}
	}
	var result map[string]interface{}
	err := r.dataCollection(projectID, collectionName).FindOne(ctx, filter).Decode(&result)
	if err != nil {
		return nil, err
	}
	return result, nil
}

// CountData returns the number of documents matching the filter.
func (r *CMSRepository) CountData(ctx context.Context, projectID, collectionName string, filter map[string]interface{}) (int64, error) {
	if filter == nil {
		filter = map[string]interface{}{}
	}
	return r.dataCollection(projectID, collectionName).CountDocuments(ctx, filter)
}

// UpdateData updates documents matching the filter.
func (r *CMSRepository) UpdateData(ctx context.Context, projectID, collectionName string, filter, update map[string]interface{}) (int64, error) {
	update["updated_at"] = time.Now().UTC()
	res, err := r.dataCollection(projectID, collectionName).UpdateMany(ctx, filter, bson.M{"$set": update})
	if err != nil {
		return 0, err
	}
	return res.ModifiedCount, nil
}

// DeleteData removes documents matching the filter.
func (r *CMSRepository) DeleteData(ctx context.Context, projectID, collectionName string, filter map[string]interface{}) (int64, error) {
	if filter == nil {
		filter = map[string]interface{}{}
	}
	res, err := r.dataCollection(projectID, collectionName).DeleteMany(ctx, filter)
	if err != nil {
		return 0, err
	}
	return res.DeletedCount, nil
}

// InsertIfNotExists inserts a document only when no document matching the filter exists.
func (r *CMSRepository) InsertIfNotExists(ctx context.Context, projectID, collectionName string, filter, doc map[string]interface{}) (interface{}, bool, error) {
	existing, err := r.FindOneData(ctx, projectID, collectionName, filter)
	if err == nil && existing != nil {
		return existing["_id"], false, nil
	}
	id, err := r.InsertData(ctx, projectID, collectionName, doc)
	if err != nil {
		return nil, false, err
	}
	return id, true, nil
}

// ---- Export Tasks ----

// CreateExportTask inserts a new export task record.
func (r *CMSRepository) CreateExportTask(ctx context.Context, t *models.ExportTask) error {
	t.ID = uuid.New().String()
	t.Status = models.ExportStatusPending
	t.CreatedAt = time.Now().UTC()
	t.UpdatedAt = time.Now().UTC()
	_, err := r.db.Collection(colExportTasks).InsertOne(ctx, t)
	return err
}

// GetExportTask retrieves an export task by its ID.
func (r *CMSRepository) GetExportTask(ctx context.Context, id string) (*models.ExportTask, error) {
	var t models.ExportTask
	err := r.db.Collection(colExportTasks).FindOne(ctx, bson.M{"_id": id}).Decode(&t)
	if err != nil {
		return nil, err
	}
	return &t, nil
}

// UpdateExportTask updates status and progress fields of an export task.
func (r *CMSRepository) UpdateExportTask(ctx context.Context, id string, update bson.M) error {
	update["updated_at"] = time.Now().UTC()
	_, err := r.db.Collection(colExportTasks).UpdateOne(
		ctx,
		bson.M{"_id": id},
		bson.M{"$set": update},
	)
	return err
}
