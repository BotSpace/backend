# Relation Field Type - Documentation

## Overview

CMS app'ga RELATION field type qo'shildi. Bu field bir collection'dan boshqa collection'ga foreign key (reference) yaratish imkonini beradi.

---

## Xususiyatlar

✅ **Foreign Key Support** - Bir collection boshqa collection'ga reference  
✅ **Self-Referencing** - Collection o'ziga o'zi reference qilishi mumkin  
✅ **Multiple Relations** - Bir collection bir nechta relation field'ga ega bo'lishi mumkin  
✅ **Validation** - Relation field'lar uchun maxsus validation  
✅ **Admin Integration** - Django admin panelda autocomplete support  

---

## O'zgarishlar

### 1. FieldType Enum

**File:** `core/apps/cms/enums/cms.py`

Yangi RELATION type qo'shildi:

```python
class FieldType(TextChoices):
    TEXT = "text", _("Text")
    NUMBER = "number", _("Number")
    BOOL = "bool", _("bool")
    DATETIME = "datetime", _("datetime")
    FILE = "file", _("file")
    AUDIO = "audio", _("audio")
    VIDEO = "video", _("video")
    PHOTO = "photo", _("photo")
    RELATION = "relation", _("Relation")  # ← YANGI
```

### 2. FieldModel

**File:** `core/apps/cms/models/cms.py`

Yangi `relation_collection` field qo'shildi:

```python
class FieldModel(AbstractBaseModel):
    collection = models.ForeignKey("CollectionModel", ...)
    name = models.CharField(...)
    type = models.CharField(...)
    required = models.BooleanField(...)
    default = models.CharField(...)
    
    # YANGI field
    relation_collection = models.ForeignKey(
        "CollectionModel",
        on_delete=models.SET_NULL,
        related_name="related_fields",
        null=True,
        blank=True,
        help_text=_("Referenced collection for RELATION type fields")
    )
```

**Tushuntirish:**
- `on_delete=models.SET_NULL` - Referenced collection o'chirilsa, field null bo'ladi
- `related_name="related_fields"` - Teskari bog'lanish nomi
- `null=True, blank=True` - Majburiy emas (faqat RELATION type uchun kerak)

### 3. Validation

**File:** `core/apps/cms/services/collection.py`

Relation field'lar uchun validation qo'shildi:

```python
elif field.type == FieldType.RELATION.value:
    # Validate relation field
    if value is not None:
        if isinstance(value, dict):
            # Object with _id
            if "_id" not in value:
                errors[field.name] = [_("Relation field must contain _id")]
        elif not isinstance(value, str):
            # Must be ObjectId string or object
            errors[field.name] = [_("Relation field must be string ObjectId or object with _id")]
```

**Valid values:**
```javascript
// String ObjectId
{ "author": "507f1f77bcf86cd799439011" }

// Object with _id
{ "author": { "_id": "507f1f77bcf86cd799439011", "name": "John" } }
```

**Invalid values:**
```javascript
// Object without _id
{ "author": { "name": "John" } }  // ✗

// Wrong type
{ "author": 123 }  // ✗
```

### 4. Serializer

**File:** `core/apps/cms/serializers/cms/field.py`

Serializer'ga validation va relation_collection qo'shildi:

```python
class BaseFieldSerializer(serializers.ModelSerializer):
    class Meta:
        fields = [
            ...
            "relation_collection",  # ← YANGI
        ]
    
    def validate(self, data):
        """Validate that relation_collection is set for RELATION type"""
        field_type = data.get('type')
        relation_collection = data.get('relation_collection')
        
        if field_type == FieldType.RELATION.value:
            if not relation_collection:
                raise serializers.ValidationError({
                    "relation_collection": "Required for RELATION type"
                })
        else:
            # Clear for non-relation fields
            data['relation_collection'] = None
        
        return data


class RetrieveFieldSerializer(BaseFieldSerializer):
    relation_collection_name = serializers.CharField(
        source='relation_collection.name',
        read_only=True
    )
    
    class Meta(BaseFieldSerializer.Meta):
        fields = BaseFieldSerializer.Meta.fields + ["relation_collection_name"]
```

### 5. Admin Panel

**File:** `core/apps/cms/admin/cms.py`

Admin panelga autocomplete qo'shildi:

```python
class FieldsInline(TabularInline):
    model = FieldModel
    fk_name = "collection"  # Which FK to use
    fields = [
        "name",
        "type",
        "required",
        "relation_collection",  # ← YANGI
    ]
    autocomplete_fields = ["relation_collection"]  # ← Autocomplete


@admin.register(CollectionModel)
class CollectionAdmin(ModelAdmin):
    ...
    search_fields = ["name"]  # ← For autocomplete
```

---

## Foydalanish

### API orqali Field yaratish

**POST** `/api/collection/{collection_name}/?project={project_id}`

```json
{
  "name": "posts",
  "fields": [
    {
      "name": "title",
      "type": "text",
      "required": true
    },
    {
      "name": "author",
      "type": "relation",
      "required": true,
      "relation_collection": 1  // users collection ID
    },
    {
      "name": "category",
      "type": "relation",
      "required": false,
      "relation_collection": 2  // categories collection ID
    }
  ]
}
```

### Ma'lumot qo'shish (Relation bilan)

**POST** `/api/collection/posts/query/?action=insert&project={project_id}`

```json
{
  "data": {
    "title": "My First Post",
    "author": "507f1f77bcf86cd799439011",  // ObjectId string
    "category": {
      "_id": "507f191e810c19729de860ea",
      "name": "Technology"
    }
  }
}
```

### Self-Referencing (O'ziga havola)

Comments collection o'ziga o'zi reference qilishi (parent comment):

```json
{
  "name": "comments",
  "fields": [
    {
      "name": "text",
      "type": "text",
      "required": true
    },
    {
      "name": "parent",
      "type": "relation",
      "required": false,
      "relation_collection": null  // Will be set to self after creation
    }
  ]
}
```

Keyin:
```python
comment_collection = CollectionModel.objects.get(name="comments")
parent_field = comment_collection.fields.get(name="parent")
parent_field.relation_collection = comment_collection
parent_field.save()
```

### Multiple Relations

Bir collection bir nechta relation field:

```json
{
  "name": "orders",
  "fields": [
    {
      "name": "customer",
      "type": "relation",
      "relation_collection": 1  // users
    },
    {
      "name": "product",
      "type": "relation",
      "relation_collection": 2  // products
    },
    {
      "name": "delivery_address",
      "type": "relation",
      "relation_collection": 3  // addresses
    }
  ]
}
```

---

## Database Schema

### Migration

**File:** `core/apps/cms/migrations/0009_add_relation_field_type.py`

```sql
-- Add relation_collection field
ALTER TABLE field 
ADD COLUMN relation_collection_id BIGINT NULL
REFERENCES collection(id) ON DELETE SET NULL;

-- Update field type choices
ALTER TABLE field 
ALTER COLUMN type TYPE VARCHAR(255);
```

### Schema Diagram

```
┌─────────────────┐
│  CollectionModel│
├─────────────────┤
│ id              │
│ name            │
│ user_id         │
│ project_id      │
└─────────────────┘
        ▲
        │ collection (FK)
        │
┌───────┴─────────┐
│   FieldModel    │
├─────────────────┤
│ id              │
│ collection_id   │───┐
│ name            │   │
│ type            │   │ relation_collection (FK)
│ required        │   │ (optional, faqat RELATION type uchun)
│ default         │   │
│ relation_coll...├───┘ (o'ziga yoki boshqa collection'ga)
└─────────────────┘
```

---

## Testlar

**File:** `core/apps/cms/tests/cms/test_relation_field.py`

### Test Coverage

```
✅ test_create_relation_field           - RELATION field yaratish
✅ test_relation_field_serializer_validation - Validation tekshirish
✅ test_relation_field_data_validation  - Ma'lumot validation
✅ test_multiple_relation_fields        - Ko'p relation field'lar
✅ test_self_referencing_relation       - O'ziga reference

5 passed in 1.10s
All project tests: 95 passed, 1 skipped
```

### Test Misollari

```python
# Create relation field
author_field = FieldModel.objects.create(
    collection=posts_collection,
    name="author",
    type=FieldType.RELATION.value,
    relation_collection=users_collection,
    required=True
)

# Validate data
data = {"author": "507f1f77bcf86cd799439011"}
errors, valid = collection_validate_data(posts_collection, data)
assert valid is True

# Invalid data
data = {"author": {"name": "John"}}  # Missing _id
errors, valid = collection_validate_data(posts_collection, data)
assert valid is False
assert "author" in errors
```

---

## Frontend Misol

### React Component

```jsx
function CreatePost() {
  const [formData, setFormData] = useState({
    title: '',
    author: null,
    category: null
  });
  
  const [authors, setAuthors] = useState([]);
  const [categories, setCategories] = useState([]);
  
  useEffect(() => {
    // Load authors (users collection)
    fetch('/api/collection/users/query/?action=find&project=1')
      .then(res => res.json())
      .then(data => setAuthors(data.data.data));
    
    // Load categories
    fetch('/api/collection/categories/query/?action=find&project=1')
      .then(res => res.json())
      .then(data => setCategories(data.data.data));
  }, []);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const postData = {
      data: {
        title: formData.title,
        author: formData.author._id,  // Send only ObjectId
        category: formData.category._id
      }
    };
    
    const res = await fetch(
      '/api/collection/posts/query/?action=insert&project=1',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(postData)
      }
    );
    
    const result = await res.json();
    console.log('Post created:', result);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={formData.title}
        onChange={(e) => setFormData({...formData, title: e.target.value})}
        placeholder="Title"
      />
      
      <select
        value={formData.author?._id}
        onChange={(e) => {
          const author = authors.find(a => a._id === e.target.value);
          setFormData({...formData, author});
        }}
      >
        <option value="">Select Author</option>
        {authors.map(author => (
          <option key={author._id} value={author._id}>
            {author.name}
          </option>
        ))}
      </select>
      
      <select
        value={formData.category?._id}
        onChange={(e) => {
          const category = categories.find(c => c._id === e.target.value);
          setFormData({...formData, category});
        }}
      >
        <option value="">Select Category</option>
        {categories.map(category => (
          <option key={category._id} value={category._id}>
            {category.name}
          </option>
        ))}
      </select>
      
      <button type="submit">Create Post</button>
    </form>
  );
}
```

---

## Use Cases

### 1. Blog System

```
users (collection)
  - name
  - email

categories (collection)
  - name
  - slug

posts (collection)
  - title
  - content
  - author (relation → users)
  - category (relation → categories)

comments (collection)
  - text
  - author (relation → users)
  - post (relation → posts)
  - parent (relation → comments) // self-reference
```

### 2. E-commerce

```
customers (collection)
  - name
  - email

products (collection)
  - name
  - price

addresses (collection)
  - street
  - city
  - customer (relation → customers)

orders (collection)
  - order_number
  - customer (relation → customers)
  - delivery_address (relation → addresses)
  
order_items (collection)
  - order (relation → orders)
  - product (relation → products)
  - quantity
```

### 3. Organizational Structure

```
departments (collection)
  - name
  
employees (collection)
  - name
  - email
  - department (relation → departments)
  - manager (relation → employees) // self-reference
```

---

## MongoDB'da Qanday Ishlaydi

### Data Storage

MongoDB'da relation field oddiy field sifatida saqlanadi, lekin qiymat ObjectId yoki object bo'ladi:

```javascript
// posts collection document
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "title": "My First Post",
  "author": ObjectId("507f191e810c19729de860ea"),  // Reference to users
  "category": {
    "_id": ObjectId("507f191e810c19729de860eb"),
    "name": "Technology"  // Denormalized data
  }
}
```

### Populate (Frontend'da)

Relation'larni populate qilish uchun frontend'da alohida query:

```javascript
// 1. Get post
const post = await fetch('/api/collection/posts/query/?action=find_one', {
  method: 'POST',
  body: JSON.stringify({ where: { _id: postId } })
}).then(r => r.json());

// 2. Get author
if (post.data.author) {
  const author = await fetch('/api/collection/users/query/?action=find_one', {
    method: 'POST',
    body: JSON.stringify({ 
      where: { _id: post.data.author } 
    })
  }).then(r => r.json());
  
  post.data.author_data = author.data;
}

// 3. Get category
if (post.data.category?._id) {
  const category = await fetch('/api/collection/categories/query/?action=find_one', {
    method: 'POST',
    body: JSON.stringify({ 
      where: { _id: post.data.category._id } 
    })
  }).then(r => r.json());
  
  post.data.category_data = category.data;
}
```

---

## Best Practices

### 1. Naming Convention

```python
# ✓ Good
author = relation to users
category = relation to categories
parent = relation to same collection

# ✗ Bad  
user_id = confusing with traditional FK
cat = unclear name
```

### 2. Required vs Optional

```python
# Required for critical relations
author = models.ForeignKey(..., required=True)

# Optional for additional data
tags = models.ForeignKey(..., required=False)
```

### 3. Denormalization

Ba'zi hollarda relation bilan birga ma'lumot denormalize qiling:

```javascript
// Instead of just ID
{ "author": "507f..." }

// Store with name for faster display
{ 
  "author": {
    "_id": "507f...",
    "name": "John Doe"
  }
}
```

### 4. Validation

Har doim relation field'larning mavjudligini tekshiring:

```python
if field.type == FieldType.RELATION.value:
    if not field.relation_collection:
        raise ValidationError("relation_collection required")
```

---

## Migration

### Apply Migration

```bash
# Docker ichida
docker compose exec web python manage.py migrate cms

# Local
python manage.py migrate cms
```

### Rollback (agar kerak bo'lsa)

```bash
python manage.py migrate cms 0008
```

---

## Kelajak Rivojlanish

### Mumkin bo'lgan Qo'shimchalar

- [ ] Cascade delete options
- [ ] On-delete actions configuration
- [ ] Automatic populate in API responses
- [ ] Many-to-many relations
- [ ] Relation validation (check if referenced doc exists)
- [ ] Circular reference detection
- [ ] Index creation for relation fields

---

## Summary

### O'zgartirilgan Fayllar (6 ta)

```
core/apps/cms/
  enums/cms.py                    - +RELATION type
  models/cms.py                   - +relation_collection field
  services/collection.py          - +relation validation
  serializers/cms/field.py        - +serializer validation
  admin/cms.py                    - +autocomplete, fk_name
  migrations/0009_*.py            - DB migration

core/apps/cms/tests/cms/
  test_relation_field.py          - NEW (5 tests)
```

### Test Results

```
Relation Field Tests: ✅ 5 passed
All Project Tests:    ✅ 95 passed, 1 skipped
Time:                 10.16 seconds
```

### Key Benefits

✅ **Flexible Relationships** - Istalgan collection'lar o'rtasida bog'lanish  
✅ **Self-Referencing** - Hierarchical data structures  
✅ **Multiple Relations** - Bir collection ko'p relation'lar  
✅ **Type Safety** - Validation orqali xatoliklarni oldini olish  
✅ **Admin Friendly** - Autocomplete qulaylik  

---

**Versiya**: 1.0.0  
**Sana**: 2025-12-02  
**Status**: ✅ Production Ready  
**Tests**: ✅ 95 passed, 1 skipped

---

## Update (2025-12-02)

### relation_collection Name Instead of ID

**Change:** RetrieveFieldSerializer endi `relation_collection` ni ID o'rniga name qaytaradi.

**Before:**
```json
{
  "id": 1,
  "name": "author",
  "type": "relation",
  "relation_collection": 22,  // ID
  "relation_collection_name": "users"
}
```

**After:**
```json
{
  "id": 1,
  "name": "author",
  "type": "relation",
  "relation_collection": "users"  // Name
}
```

### Why?

Frontend uchun osonroq - ID dan name kerakroq:

```javascript
// Collection retrieve
const collection = await api.get('/collection/posts/?project=1');

collection.fields.forEach(field => {
  if (field.type === 'relation') {
    console.log(`${field.name} → ${field.relation_collection}`);
    // Output: "author → users"
  }
});
```

### Create/Update

Create va Update uchun hali ham ID ishlatiladi:

```json
{
  "name": "author",
  "type": "relation",
  "relation_collection": 1  // ID kerak
}
```

Bu normal - yaratish/yangilash uchun ID kerak, ko'rsatish uchun name qulay.

---

**Tests:** ✅ 95 passed, 1 skipped  
**Migration:** ✅ Applied (0009_add_relation_field_type)
