package repository

import (
	"errors"

	"github.com/botspace/template-service/internal/models"
	"gorm.io/gorm"
)

// TemplateRepository provides all database operations for the template service.
type TemplateRepository struct {
	db *gorm.DB
}

// New creates a new TemplateRepository.
func New(db *gorm.DB) *TemplateRepository {
	return &TemplateRepository{db: db}
}

// DB exposes the underlying *gorm.DB for advanced queries.
func (r *TemplateRepository) DB() *gorm.DB {
	return r.db
}

// AutoMigrate runs GORM auto-migration for all template models.
func AutoMigrate(db *gorm.DB) error {
	return db.AutoMigrate(
		&models.TemplateCategory{},
		&models.TemplateFeature{},
		&models.Template{},
		&models.TemplateLike{},
		&models.UserTemplate{},
		&models.TemplateOrder{},
		&models.TemplateSubmission{},
		&models.TemplateWithdrawal{},
	)
}

// ---- Templates ----

func (r *TemplateRepository) ListTemplates(page, pageSize int) ([]models.Template, int64, error) {
	var templates []models.Template
	var total int64

	offset := (page - 1) * pageSize
	query := r.db.Where("is_verify = ?", true)

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}
	if err := query.Preload("Features").Preload("Categories").Offset(offset).Limit(pageSize).Find(&templates).Error; err != nil {
		return nil, 0, err
	}
	return templates, total, nil
}

func (r *TemplateRepository) GetTemplateBySlug(slug string) (*models.Template, error) {
	var t models.Template
	err := r.db.Where("slug = ? AND is_verify = ?", slug, true).
		Preload("Features").Preload("Categories").First(&t).Error
	if err != nil {
		return nil, err
	}
	return &t, nil
}

func (r *TemplateRepository) GetTemplateByID(id uint) (*models.Template, error) {
	var t models.Template
	err := r.db.Preload("Features").Preload("Categories").First(&t, id).Error
	if err != nil {
		return nil, err
	}
	return &t, nil
}

func (r *TemplateRepository) IncrementViews(id uint) {
	r.db.Model(&models.Template{}).Where("id = ?", id).UpdateColumn("views", gorm.Expr("views + ?", 1))
}

// ---- Categories ----

func (r *TemplateRepository) ListCategories() ([]models.TemplateCategory, error) {
	var cats []models.TemplateCategory
	return cats, r.db.Find(&cats).Error
}

// ---- Features ----

func (r *TemplateRepository) ListFeatures() ([]models.TemplateFeature, error) {
	var features []models.TemplateFeature
	return features, r.db.Find(&features).Error
}

// ---- User Templates ----

func (r *TemplateRepository) ListUserTemplates(userID uint) ([]models.UserTemplate, error) {
	var items []models.UserTemplate
	return items, r.db.Where("user_id = ?", userID).Find(&items).Error
}

// ---- Orders ----

func (r *TemplateRepository) GetOrCreateOrder(userID, templateID uint, amount float64) (*models.TemplateOrder, bool, error) {
	var order models.TemplateOrder
	err := r.db.Where("user_id = ? AND template_id = ?", userID, templateID).First(&order).Error
	if err == nil {
		return &order, false, nil
	}
	if !errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, false, err
	}

	order = models.TemplateOrder{
		UserID:     userID,
		TemplateID: templateID,
		Amount:     amount,
		Status:     models.OrderStatusPending,
	}
	// Free templates are auto-confirmed
	if amount == 0 {
		order.Status = models.OrderStatusConfirm
		order.PaymentStatus = true
	}
	if err := r.db.Create(&order).Error; err != nil {
		return nil, false, err
	}
	return &order, true, nil
}

func (r *TemplateRepository) ListOrders(userID uint) ([]models.TemplateOrder, error) {
	var orders []models.TemplateOrder
	return orders, r.db.Where("user_id = ?", userID).Find(&orders).Error
}

func (r *TemplateRepository) GetOrder(id, userID uint) (*models.TemplateOrder, error) {
	var order models.TemplateOrder
	return &order, r.db.Where("id = ? AND user_id = ?", id, userID).First(&order).Error
}

func (r *TemplateRepository) ConfirmOrder(orderID uint) error {
	return r.db.Model(&models.TemplateOrder{}).Where("id = ?", orderID).
		Updates(map[string]interface{}{
			"status":         models.OrderStatusConfirm,
			"payment_status": true,
		}).Error
}

// ---- Submissions ----

func (r *TemplateRepository) CreateSubmission(s *models.TemplateSubmission) error {
	return r.db.Create(s).Error
}

func (r *TemplateRepository) ListSubmissions(userID uint) ([]models.TemplateSubmission, error) {
	var items []models.TemplateSubmission
	return items, r.db.Where("user_id = ?", userID).Find(&items).Error
}

func (r *TemplateRepository) GetSubmission(id, userID uint) (*models.TemplateSubmission, error) {
	var s models.TemplateSubmission
	return &s, r.db.Where("id = ? AND user_id = ?", id, userID).First(&s).Error
}

func (r *TemplateRepository) UpdateSubmission(id, userID uint, updates map[string]interface{}) error {
	result := r.db.Model(&models.TemplateSubmission{}).
		Where("id = ? AND user_id = ? AND status = ?", id, userID, models.SubmissionStatusPending).
		Updates(updates)
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return result.Error
}

func (r *TemplateRepository) DeleteSubmission(id, userID uint) error {
	result := r.db.Where("id = ? AND user_id = ? AND status = ?", id, userID, models.SubmissionStatusPending).
		Delete(&models.TemplateSubmission{})
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return result.Error
}

// ---- Withdrawals ----

func (r *TemplateRepository) CreateWithdrawal(w *models.TemplateWithdrawal) error {
	return r.db.Create(w).Error
}

func (r *TemplateRepository) ListWithdrawals(userID uint) ([]models.TemplateWithdrawal, error) {
	var items []models.TemplateWithdrawal
	return items, r.db.Where("user_id = ?", userID).Find(&items).Error
}

func (r *TemplateRepository) GetWithdrawal(id, userID uint) (*models.TemplateWithdrawal, error) {
	var w models.TemplateWithdrawal
	return &w, r.db.Where("id = ? AND user_id = ?", id, userID).First(&w).Error
}

func (r *TemplateRepository) DeleteWithdrawal(id, userID uint) error {
	result := r.db.Where("id = ? AND user_id = ? AND status = ?", id, userID, models.WithdrawalStatusPending).
		Delete(&models.TemplateWithdrawal{})
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return result.Error
}
