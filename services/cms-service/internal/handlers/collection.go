package handlers

import (
	"net/http"

	"github.com/botspace/cms-service/internal/models"
	"github.com/botspace/cms-service/internal/repository"
	"github.com/botspace/cms-service/internal/streams"
	"github.com/gin-gonic/gin"
	"go.mongodb.org/mongo-driver/mongo"
)

// CollectionHandler handles HTTP requests for CMS collections.
type CollectionHandler struct {
	repo     *repository.CMSRepository
	producer *streams.Producer
}

// NewCollectionHandler constructs a CollectionHandler.
func NewCollectionHandler(repo *repository.CMSRepository, producer *streams.Producer) *CollectionHandler {
	return &CollectionHandler{repo: repo, producer: producer}
}

// List godoc
// GET /api/v1/collection?project_id=<id>
func (h *CollectionHandler) List(c *gin.Context) {
	projectID := c.Query("project_id")
	if projectID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "project_id is required"})
		return
	}

	collections, err := h.repo.ListCollections(c.Request.Context(), projectID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, collections)
}

// Create godoc
// POST /api/v1/collection
func (h *CollectionHandler) Create(c *gin.Context) {
	var col models.Collection
	if err := c.ShouldBindJSON(&col); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	userID, _ := c.Get("user_id")
	col.UserID = userID.(string)

	if err := h.repo.CreateCollection(c.Request.Context(), &col); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	_ = h.producer.PublishCollectionCreated(c.Request.Context(), col.ID, col.ProjectID, col.Name)
	c.JSON(http.StatusCreated, col)
}

// Get godoc
// GET /api/v1/collection/:id
func (h *CollectionHandler) Get(c *gin.Context) {
	id := c.Param("id")
	col, err := h.repo.GetCollectionByID(c.Request.Context(), id)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			c.JSON(http.StatusNotFound, gin.H{"error": "collection not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, col)
}

// Update godoc
// PATCH /api/v1/collection/:id
func (h *CollectionHandler) Update(c *gin.Context) {
	id := c.Param("id")
	var body map[string]interface{}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Only allow updating safe fields
	allowed := map[string]bool{"name": true}
	update := make(map[string]interface{})
	for k, v := range body {
		if allowed[k] {
			update[k] = v
		}
	}

	if len(update) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "no updatable fields provided"})
		return
	}

	if err := h.repo.UpdateCollection(c.Request.Context(), id, update); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "updated"})
}

// Delete godoc
// DELETE /api/v1/collection/:id
func (h *CollectionHandler) Delete(c *gin.Context) {
	id := c.Param("id")

	// Retrieve the collection to check if deletion is allowed and get its name.
	col, err := h.repo.GetCollectionByID(c.Request.Context(), id)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			c.JSON(http.StatusNotFound, gin.H{"error": "collection not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Protect system collections
	protected := map[string]bool{"users": true, "chat": true}
	if protected[col.Name] {
		c.JSON(http.StatusForbidden, gin.H{"error": "cannot delete system collection"})
		return
	}

	if err := h.repo.DeleteCollection(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Clean up all fields associated with this collection
	_ = h.repo.DeleteFieldsByCollection(c.Request.Context(), id)

	_ = h.producer.PublishCollectionDeleted(c.Request.Context(), id, col.ProjectID)
	c.JSON(http.StatusNoContent, nil)
}

// ListFields godoc
// GET /api/v1/collection/:id/fields
func (h *CollectionHandler) ListFields(c *gin.Context) {
	collectionID := c.Param("id")
	fields, err := h.repo.ListFields(c.Request.Context(), collectionID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, fields)
}

// CreateField godoc
// POST /api/v1/collection/:id/fields
func (h *CollectionHandler) CreateField(c *gin.Context) {
	collectionID := c.Param("id")

	var f models.Field
	if err := c.ShouldBindJSON(&f); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	f.CollectionID = collectionID

	if err := h.repo.CreateField(c.Request.Context(), &f); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, f)
}

// Query godoc
// POST /api/v1/collection/:id/query
// Supported actions: find, find_one, count, insert, update, delete, insert_if_not_exists
func (h *CollectionHandler) Query(c *gin.Context) {
	id := c.Param("id")

	col, err := h.repo.GetCollectionByID(c.Request.Context(), id)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			c.JSON(http.StatusNotFound, gin.H{"error": "collection not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	var req models.QueryRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := c.Request.Context()

	switch req.Action {
	case "find":
		result, err := h.repo.FindData(ctx, col.ProjectID, col.Name, req.Filter, req.Limit, req.Skip)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"data": result})

	case "find_one":
		result, err := h.repo.FindOneData(ctx, col.ProjectID, col.Name, req.Filter)
		if err != nil {
			if err == mongo.ErrNoDocuments {
				c.JSON(http.StatusNotFound, gin.H{"data": nil})
				return
			}
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"data": result})

	case "count":
		n, err := h.repo.CountData(ctx, col.ProjectID, col.Name, req.Filter)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"count": n})

	case "insert":
		if req.Data == nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "data is required for insert"})
			return
		}
		insertedID, err := h.repo.InsertData(ctx, col.ProjectID, col.Name, req.Data)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusCreated, gin.H{"id": insertedID})

	case "update":
		if req.Filter == nil || req.Data == nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "filter and data are required for update"})
			return
		}
		n, err := h.repo.UpdateData(ctx, col.ProjectID, col.Name, req.Filter, req.Data)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"modified": n})

	case "delete":
		n, err := h.repo.DeleteData(ctx, col.ProjectID, col.Name, req.Filter)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"deleted": n})

	case "insert_if_not_exists":
		if req.Filter == nil || req.Data == nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "filter and data are required for insert_if_not_exists"})
			return
		}
		insertedID, created, err := h.repo.InsertIfNotExists(ctx, col.ProjectID, col.Name, req.Filter, req.Data)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"id": insertedID, "created": created})

	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "unsupported action: " + req.Action})
	}
}

// ExportStatus godoc
// GET /api/v1/collection/export-status/:task_id
func (h *CollectionHandler) ExportStatus(c *gin.Context) {
	taskID := c.Param("task_id")
	task, err := h.repo.GetExportTask(c.Request.Context(), taskID)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, task)
}

// ExportExcel godoc
// POST /api/v1/collection/:id/export-excel
func (h *CollectionHandler) ExportExcel(c *gin.Context) {
	id := c.Param("id")

	col, err := h.repo.GetCollectionByID(c.Request.Context(), id)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			c.JSON(http.StatusNotFound, gin.H{"error": "collection not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	task := &models.ExportTask{
		CollectionID: col.ID,
		Status:       models.ExportStatusPending,
	}
	if err := h.repo.CreateExportTask(c.Request.Context(), task); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// In a production system this would enqueue a background worker via Redis Streams.
	c.JSON(http.StatusAccepted, gin.H{"task_id": task.ID})
}
