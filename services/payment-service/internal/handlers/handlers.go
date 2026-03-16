package handlers

import (
	"fmt"
	"net/http"
	"strconv"

	"github.com/botspace/payment-service/internal/config"
	"github.com/botspace/payment-service/internal/models"
	"github.com/botspace/payment-service/internal/repository"
	"github.com/botspace/payment-service/internal/streams"
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// ---- Transaction ----

// TransactionHandler handles read-only transaction endpoints.
type TransactionHandler struct {
	repo *repository.PaymentRepository
}

// NewTransactionHandler constructs a TransactionHandler.
func NewTransactionHandler(repo *repository.PaymentRepository) *TransactionHandler {
	return &TransactionHandler{repo: repo}
}

func (h *TransactionHandler) List(c *gin.Context) {
	uid := userID(c)
	items, err := h.repo.ListTransactions(uid)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, items)
}

func (h *TransactionHandler) Get(c *gin.Context) {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 64)
	uid := userID(c)
	t, err := h.repo.GetTransaction(uint(id), uid)
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "transaction not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, t)
}

// ---- History ----

// HistoryHandler handles balance history endpoints.
type HistoryHandler struct {
	repo *repository.PaymentRepository
}

// NewHistoryHandler constructs a HistoryHandler.
func NewHistoryHandler(repo *repository.PaymentRepository) *HistoryHandler {
	return &HistoryHandler{repo: repo}
}

func (h *HistoryHandler) List(c *gin.Context) {
	uid := userID(c)
	items, err := h.repo.ListHistory(uid)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, items)
}

func (h *HistoryHandler) Get(c *gin.Context) {
	id, _ := strconv.ParseUint(c.Param("id"), 10, 64)
	uid := userID(c)
	h2, err := h.repo.GetHistory(uint(id), uid)
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "history not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, h2)
}

// ---- Payment link ----

// PaymentLinkHandler creates payment gateway links.
type PaymentLinkHandler struct {
	repo     *repository.PaymentRepository
	cfg      *config.Config
	producer *streams.Producer
}

// NewPaymentLinkHandler constructs a PaymentLinkHandler.
func NewPaymentLinkHandler(repo *repository.PaymentRepository, cfg *config.Config, producer *streams.Producer) *PaymentLinkHandler {
	return &PaymentLinkHandler{repo: repo, cfg: cfg, producer: producer}
}

// Create godoc
// POST /api/v1/payment/create-transaction
func (h *PaymentLinkHandler) Create(c *gin.Context) {
	uid := userID(c)

	var req struct {
		Method string  `json:"method" binding:"required,oneof=click payme"`
		Amount float64 `json:"amount" binding:"required,gt=0"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Create the transaction record first
	txn := &models.Transaction{
		UserID: uid,
		Amount: req.Amount,
		Status: false,
	}
	if err := h.repo.CreateTransaction(txn); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Build the gateway redirect URL
	link := buildPaymentLink(req.Method, txn.ID, req.Amount, h.cfg)
	c.JSON(http.StatusOK, gin.H{"link": link})
}

// buildPaymentLink constructs the payment gateway URL.
// In production this would call the actual SDK; here we build the URL template.
func buildPaymentLink(method string, txnID uint, amount float64, cfg *config.Config) string {
	amountTiyin := int64(amount * 100) // Payme/Click use tiyin (1/100 UZS)
	switch method {
	case "click":
		return fmt.Sprintf(
			"https://my.click.uz/services/pay?service_id=%s&merchant_id=%s&amount=%d&transaction_param=%d",
			cfg.ClickServiceID,
			cfg.ClickMerchantID,
			amountTiyin,
			txnID,
		)
	case "payme":
		return fmt.Sprintf(
			"https://checkout.paycom.uz/%s?amount=%d&order=%d",
			cfg.PaymeID,
			amountTiyin,
			txnID,
		)
	}
	return ""
}

// ---- Click webhook ----

// ClickWebhookHandler handles callbacks from the Click payment gateway.
type ClickWebhookHandler struct {
	repo     *repository.PaymentRepository
	producer *streams.Producer
}

// NewClickWebhookHandler constructs a ClickWebhookHandler.
func NewClickWebhookHandler(repo *repository.PaymentRepository, producer *streams.Producer) *ClickWebhookHandler {
	return &ClickWebhookHandler{repo: repo, producer: producer}
}

// Update godoc
// POST /api/v1/payment/click/update
func (h *ClickWebhookHandler) Update(c *gin.Context) {
	var req struct {
		TransactionID uint    `json:"merchant_trans_id" binding:"required"`
		Amount        float64 `json:"amount"`
		Error         int     `json:"error"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	txn, err := h.repo.GetTransactionByIDOnly(req.TransactionID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "transaction not found"})
		return
	}

	if req.Error == 0 {
		// Payment succeeded
		if err := h.repo.MarkTransactionComplete(txn.ID); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		if err := h.repo.AddBalance(txn.UserID, txn.Amount, "click payment"); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		_ = h.producer.PublishPaymentSuccess(c.Request.Context(), txn.ID, txn.UserID, txn.Amount, txn.OrderID)
	} else {
		// Payment failed/cancelled
		if err := h.repo.SubtractBalance(txn.UserID, txn.Amount, "click payment cancelled"); err != nil {
			// Non-fatal: balance may already be 0
			_ = err
		}
		_ = h.producer.PublishPaymentFailed(c.Request.Context(), txn.ID, txn.UserID, txn.Amount)
	}

	c.JSON(http.StatusOK, gin.H{"error": 0, "error_note": "Success"})
}

// ---- Payme webhook ----

// PaymeWebhookHandler handles callbacks from the Payme payment gateway.
type PaymeWebhookHandler struct {
	repo     *repository.PaymentRepository
	producer *streams.Producer
}

// NewPaymeWebhookHandler constructs a PaymeWebhookHandler.
func NewPaymeWebhookHandler(repo *repository.PaymentRepository, producer *streams.Producer) *PaymeWebhookHandler {
	return &PaymeWebhookHandler{repo: repo, producer: producer}
}

// Update godoc
// POST /api/v1/payment/payme/update
func (h *PaymeWebhookHandler) Update(c *gin.Context) {
	var req struct {
		Method string                 `json:"method"`
		Params map[string]interface{} `json:"params"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	switch req.Method {
	case "PerformTransaction":
		h.handleSuccess(c, req.Params)
	case "CancelTransaction":
		h.handleCancel(c, req.Params)
	default:
		c.JSON(http.StatusOK, gin.H{"result": "ok"})
	}
}

func (h *PaymeWebhookHandler) handleSuccess(c *gin.Context, params map[string]interface{}) {
	txnIDRaw, _ := params["id"].(float64)
	txnID := uint(txnIDRaw)

	txn, err := h.repo.GetTransactionByIDOnly(txnID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "transaction not found"})
		return
	}

	if err := h.repo.MarkTransactionComplete(txn.ID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if err := h.repo.AddBalance(txn.UserID, txn.Amount, "payme payment"); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	_ = h.producer.PublishPaymentSuccess(c.Request.Context(), txn.ID, txn.UserID, txn.Amount, txn.OrderID)
	c.JSON(http.StatusOK, gin.H{"result": map[string]interface{}{"transaction": txn.ID}})
}

func (h *PaymeWebhookHandler) handleCancel(c *gin.Context, params map[string]interface{}) {
	txnIDRaw, _ := params["id"].(float64)
	txnID := uint(txnIDRaw)

	txn, err := h.repo.GetTransactionByIDOnly(txnID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "transaction not found"})
		return
	}

	if err := h.repo.SubtractBalance(txn.UserID, txn.Amount, "payme payment cancelled"); err != nil {
		_ = err
	}
	_ = h.producer.PublishPaymentFailed(c.Request.Context(), txn.ID, txn.UserID, txn.Amount)
	c.JSON(http.StatusOK, gin.H{"result": map[string]interface{}{"transaction": txn.ID}})
}
