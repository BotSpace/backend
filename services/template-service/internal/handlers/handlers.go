package handlers

import (
	"net/http"
	"strconv"

	"github.com/botspace/template-service/internal/models"
	"github.com/botspace/template-service/internal/repository"
	"github.com/botspace/template-service/internal/streams"
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// TemplateHandler handles template listing and detail endpoints.
type TemplateHandler struct {
	repo *repository.TemplateRepository
}

// NewTemplateHandler constructs a TemplateHandler.
func NewTemplateHandler(repo *repository.TemplateRepository) *TemplateHandler {
	return &TemplateHandler{repo: repo}
}

// List godoc GET /api/v1/template/list
func (h *TemplateHandler) List(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))
	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 20
	}

	templates, total, err := h.repo.ListTemplates(page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"count": total, "results": templates})
}

// Get godoc GET /api/v1/template/list/:slug
func (h *TemplateHandler) Get(c *gin.Context) {
	slug := c.Param("slug")
	t, err := h.repo.GetTemplateBySlug(slug)
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "template not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	go h.repo.IncrementViews(t.ID)
	c.JSON(http.StatusOK, t)
}

// ---- Categories ----

type CategoryHandler struct {
	repo *repository.TemplateRepository
}

func NewCategoryHandler(repo *repository.TemplateRepository) *CategoryHandler {
	return &CategoryHandler{repo: repo}
}

func (h *CategoryHandler) List(c *gin.Context) {
	cats, err := h.repo.ListCategories()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, cats)
}

// ---- Features ----

type FeatureHandler struct {
	repo *repository.TemplateRepository
}

func NewFeatureHandler(repo *repository.TemplateRepository) *FeatureHandler {
	return &FeatureHandler{repo: repo}
}

func (h *FeatureHandler) List(c *gin.Context) {
	features, err := h.repo.ListFeatures()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, features)
}

// ---- User Templates ----

type UserTemplateHandler struct {
	repo *repository.TemplateRepository
}

func NewUserTemplateHandler(repo *repository.TemplateRepository) *UserTemplateHandler {
	return &UserTemplateHandler{repo: repo}
}

func (h *UserTemplateHandler) List(c *gin.Context) {
	uid := userID(c)
	items, err := h.repo.ListUserTemplates(uid)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, items)
}

// ---- Orders ----

type OrderHandler struct {
	repo     *repository.TemplateRepository
	producer *streams.Producer
}

func NewOrderHandler(repo *repository.TemplateRepository, producer *streams.Producer) *OrderHandler {
	return &OrderHandler{repo: repo, producer: producer}
}

func (h *OrderHandler) List(c *gin.Context) {
	uid := userID(c)
	orders, err := h.repo.ListOrders(uid)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, orders)
}

func (h *OrderHandler) Create(c *gin.Context) {
	uid := userID(c)

	var req struct {
		TemplateID uint `json:"template_id" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Fetch template to determine price
	tmpl, err := h.repo.GetTemplateByID(req.TemplateID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "template not found"})
		return
	}

	order, created, err := h.repo.GetOrCreateOrder(uid, req.TemplateID, tmpl.Price())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if created {
		_ = h.producer.PublishOrderCreated(c.Request.Context(), order.ID, uid, req.TemplateID, order.Amount)
	}

	c.JSON(http.StatusCreated, order)
}

func (h *OrderHandler) Get(c *gin.Context) {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 64)
	uid := userID(c)
	order, err := h.repo.GetOrder(uint(id), uid)
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "order not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, order)
}

// ---- Submissions ----

type SubmissionHandler struct {
	repo *repository.TemplateRepository
}

func NewSubmissionHandler(repo *repository.TemplateRepository) *SubmissionHandler {
	return &SubmissionHandler{repo: repo}
}

func (h *SubmissionHandler) List(c *gin.Context) {
	uid := userID(c)
	items, err := h.repo.ListSubmissions(uid)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, items)
}

func (h *SubmissionHandler) Create(c *gin.Context) {
	uid := userID(c)
	var s models.TemplateSubmission
	if err := c.ShouldBindJSON(&s); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	s.UserID = uid
	s.Status = models.SubmissionStatusPending
	if err := h.repo.CreateSubmission(&s); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, s)
}

func (h *SubmissionHandler) Get(c *gin.Context) {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 64)
	uid := userID(c)
	s, err := h.repo.GetSubmission(uint(id), uid)
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "submission not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, s)
}

func (h *SubmissionHandler) Update(c *gin.Context) {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 64)
	uid := userID(c)
	var body map[string]interface{}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.repo.UpdateSubmission(uint(id), uid, body); err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "submission not found or not editable"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "updated"})
}

func (h *SubmissionHandler) Delete(c *gin.Context) {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 64)
	uid := userID(c)
	if err := h.repo.DeleteSubmission(uint(id), uid); err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "submission not found or not deletable"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusNoContent, nil)
}

// ---- Withdrawals ----

type WithdrawalHandler struct {
	repo *repository.TemplateRepository
}

func NewWithdrawalHandler(repo *repository.TemplateRepository) *WithdrawalHandler {
	return &WithdrawalHandler{repo: repo}
}

func (h *WithdrawalHandler) List(c *gin.Context) {
	uid := userID(c)
	items, err := h.repo.ListWithdrawals(uid)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, items)
}

func (h *WithdrawalHandler) Create(c *gin.Context) {
	uid := userID(c)
	var w models.TemplateWithdrawal
	if err := c.ShouldBindJSON(&w); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	w.UserID = uid
	w.Status = models.WithdrawalStatusPending
	if err := h.repo.CreateWithdrawal(&w); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, w)
}

func (h *WithdrawalHandler) Get(c *gin.Context) {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 64)
	uid := userID(c)
	w, err := h.repo.GetWithdrawal(uint(id), uid)
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "withdrawal not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, w)
}

func (h *WithdrawalHandler) Delete(c *gin.Context) {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 64)
	uid := userID(c)
	if err := h.repo.DeleteWithdrawal(uint(id), uid); err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "withdrawal not found or not deletable"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusNoContent, nil)
}
