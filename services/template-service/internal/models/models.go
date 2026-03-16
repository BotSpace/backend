package models

import (
	"time"

	"gorm.io/gorm"
)

// DiscountType enumerates discount calculation modes.
type DiscountType string

const (
	DiscountTypePercent DiscountType = "percent"
	DiscountTypeAmount  DiscountType = "amount"
)

// TemplateCategory represents a category assigned to templates.
type TemplateCategory struct {
	ID        uint           `gorm:"primaryKey"                    json:"id"`
	Name      string         `gorm:"not null;uniqueIndex;size:255"  json:"name"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index"                         json:"-"`
}

// TemplateFeature represents a named attribute/feature tag for templates.
type TemplateFeature struct {
	ID        uint           `gorm:"primaryKey"              json:"id"`
	Name      string         `gorm:"not null;size:255"       json:"name"`
	Value     string         `gorm:"size:255"                json:"value,omitempty"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index"                   json:"-"`
}

// Template is the main marketplace template entity.
type Template struct {
	ID               uint               `gorm:"primaryKey"                          json:"id"`
	AuthorID         uint               `gorm:"not null;index"                      json:"author_id"`
	Name             string             `gorm:"not null;size:255"                   json:"name"`
	Slug             string             `gorm:"uniqueIndex;not null;size:255"       json:"slug"`
	Image            string             `gorm:"size:512"                            json:"image,omitempty"`
	Video            string             `gorm:"size:512"                            json:"video,omitempty"`
	ProjectID        uint               `gorm:"index"                               json:"project_id"`
	ShortDescription string             `gorm:"size:512"                            json:"short_description,omitempty"`
	Description      string             `gorm:"type:text"                           json:"description,omitempty"`
	OriginalPrice    float64            `gorm:"type:decimal(20,2);default:0"        json:"original_price"`
	Discount         float64            `gorm:"type:decimal(20,2);default:0"        json:"discount"`
	DiscountType     DiscountType       `gorm:"size:50;default:'percent'"           json:"discount_type"`
	Views            int64              `gorm:"default:0"                           json:"views"`
	IsVerify         bool               `gorm:"default:false"                       json:"is_verify"`
	DemoURL          string             `gorm:"size:512"                            json:"demo_url,omitempty"`
	Features         []TemplateFeature  `gorm:"many2many:template_features_m2m;"    json:"features,omitempty"`
	Categories       []TemplateCategory `gorm:"many2many:template_categories_m2m;"  json:"categories,omitempty"`
	CreatedAt        time.Time          `json:"created_at"`
	UpdatedAt        time.Time          `json:"updated_at"`
	DeletedAt        gorm.DeletedAt     `gorm:"index"                               json:"-"`
}

// Price returns the effective price after applying the discount.
func (t *Template) Price() float64 {
	switch t.DiscountType {
	case DiscountTypePercent:
		return t.OriginalPrice * (1 - t.Discount/100)
	case DiscountTypeAmount:
		price := t.OriginalPrice - t.Discount
		if price < 0 {
			return 0
		}
		return price
	default:
		return t.OriginalPrice
	}
}

// TemplateLike represents a user's "like" on a template.
type TemplateLike struct {
	ID         uint      `gorm:"primaryKey" json:"id"`
	TemplateID uint      `gorm:"not null;index" json:"template_id"`
	UserID     uint      `gorm:"not null;index" json:"user_id"`
	CreatedAt  time.Time `json:"created_at"`
}

// UserTemplate links a user to a template they have access to (purchased or free).
type UserTemplate struct {
	ID         uint      `gorm:"primaryKey" json:"id"`
	UserID     uint      `gorm:"not null;index" json:"user_id"`
	TemplateID uint      `gorm:"not null;index" json:"template_id"`
	CreatedAt  time.Time `json:"created_at"`
}

// OrderStatus enumerates template order statuses.
type OrderStatus string

const (
	OrderStatusPending OrderStatus = "pending"
	OrderStatusConfirm OrderStatus = "confirm"
)

// TemplateOrder records a user's purchase of a template.
type TemplateOrder struct {
	ID            uint           `gorm:"primaryKey"                         json:"id"`
	UserID        uint           `gorm:"not null;index"                     json:"user_id"`
	TemplateID    uint           `gorm:"not null;index"                     json:"template_id"`
	Amount        float64        `gorm:"type:decimal(20,2);default:0"       json:"amount"`
	Status        OrderStatus    `gorm:"size:50;default:'pending'"          json:"status"`
	PaymentStatus bool           `gorm:"default:false"                      json:"payment_status"`
	CommissionPaid bool          `gorm:"default:false"                      json:"commission_paid"`
	CreatedAt     time.Time      `json:"created_at"`
	UpdatedAt     time.Time      `json:"updated_at"`
	DeletedAt     gorm.DeletedAt `gorm:"index"                              json:"-"`
}

// SubmissionStatus enumerates template submission states.
type SubmissionStatus string

const (
	SubmissionStatusPending  SubmissionStatus = "pending"
	SubmissionStatusApproved SubmissionStatus = "approved"
	SubmissionStatusRejected SubmissionStatus = "rejected"
)

// TemplateSubmission is a user's request to publish a new template.
type TemplateSubmission struct {
	ID               uint               `gorm:"primaryKey"                         json:"id"`
	UserID           uint               `gorm:"not null;index"                     json:"user_id"`
	ProjectID        uint               `gorm:"index"                              json:"project_id"`
	Name             string             `gorm:"not null;size:255"                  json:"name"`
	ShortDescription string             `gorm:"size:512"                           json:"short_description,omitempty"`
	Description      string             `gorm:"type:text"                          json:"description,omitempty"`
	Image            string             `gorm:"size:512"                           json:"image,omitempty"`
	Video            string             `gorm:"size:512"                           json:"video,omitempty"`
	DemoURL          string             `gorm:"size:512"                           json:"demo_url,omitempty"`
	OriginalPrice    float64            `gorm:"type:decimal(20,2);default:0"       json:"original_price"`
	Categories       []TemplateCategory `gorm:"many2many:submission_categories_m2m;" json:"categories,omitempty"`
	Features         []TemplateFeature  `gorm:"many2many:submission_features_m2m;"   json:"features,omitempty"`
	Status           SubmissionStatus   `gorm:"size:50;default:'pending'"          json:"status"`
	RejectionReason  string             `gorm:"type:text"                          json:"rejection_reason,omitempty"`
	TemplateID       *uint              `gorm:"index"                              json:"template_id,omitempty"`
	ReviewedByID     *uint              `gorm:"index"                              json:"reviewed_by_id,omitempty"`
	ReviewedAt       *time.Time         `json:"reviewed_at,omitempty"`
	CreatedAt        time.Time          `json:"created_at"`
	UpdatedAt        time.Time          `json:"updated_at"`
	DeletedAt        gorm.DeletedAt     `gorm:"index"                              json:"-"`
}

// WithdrawalStatus enumerates withdrawal request states.
type WithdrawalStatus string

const (
	WithdrawalStatusPending  WithdrawalStatus = "pending"
	WithdrawalStatusApproved WithdrawalStatus = "approved"
	WithdrawalStatusRejected WithdrawalStatus = "rejected"
)

// TemplateWithdrawal is an author's request to withdraw earnings.
type TemplateWithdrawal struct {
	ID              uint             `gorm:"primaryKey"                        json:"id"`
	UserID          uint             `gorm:"not null;index"                    json:"user_id"`
	Amount          float64          `gorm:"type:decimal(20,2);not null"       json:"amount"`
	CardNumber      string           `gorm:"not null;size:255"                 json:"card_number"`
	CardOwner       string           `gorm:"not null;size:255"                 json:"card_owner"`
	Status          WithdrawalStatus `gorm:"size:50;default:'pending'"         json:"status"`
	RejectionReason string           `gorm:"type:text"                         json:"rejection_reason,omitempty"`
	ReviewedByID    *uint            `gorm:"index"                             json:"reviewed_by_id,omitempty"`
	ReviewedAt      *time.Time       `json:"reviewed_at,omitempty"`
	CreatedAt       time.Time        `json:"created_at"`
	UpdatedAt       time.Time        `json:"updated_at"`
	DeletedAt       gorm.DeletedAt   `gorm:"index"                             json:"-"`
}
