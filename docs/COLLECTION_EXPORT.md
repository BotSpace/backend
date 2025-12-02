# Collection Excel Export API

CMS ilovasidagi collection ma'lumotlarini Excel formatida yuklab olish funksiyasi.

## Xususiyatlar

- ✅ Celery task orqali asenkron export (timeout muammosi yo'q)
- ✅ Katta fayllar uchun batch processing
- ✅ UUID bilan task tracking
- ✅ Progress monitoring
- ✅ Tayyor bo'lganda frontend download qiladi

## API Endpoints

### 1. Export boshlash

**POST** `/api/v1/cms/collection/{collection_name}/export-excel/?project={project_id}`

Export jarayonini boshlaydi va task_id qaytaradi.

**Response:**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending",
    "file_url": null,
    "file_path": null,
    "error_message": null,
    "total_records": null,
    "processed_records": 0,
    "progress_percentage": 0.0,
    "created_at": "2025-12-02T11:00:00Z",
    "updated_at": "2025-12-02T11:00:00Z"
}
```

### 2. Status tekshirish

**GET** `/api/v1/cms/collection/export-status/{task_id}/`

Export jarayonining holatini ko'rsatadi.

**Response (Processing):**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "file_url": null,
    "file_path": null,
    "error_message": null,
    "total_records": 10000,
    "processed_records": 5000,
    "progress_percentage": 50.0,
    "created_at": "2025-12-02T11:00:00Z",
    "updated_at": "2025-12-02T11:00:30Z"
}
```

**Response (Completed):**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "file_url": "http://example.com/resources/media/exports/users_20251202_110000_550e8400-e29b-41d4-a716-446655440000.xlsx",
    "file_path": "exports/users_20251202_110000_550e8400-e29b-41d4-a716-446655440000.xlsx",
    "error_message": null,
    "total_records": 10000,
    "processed_records": 10000,
    "progress_percentage": 100.0,
    "created_at": "2025-12-02T11:00:00Z",
    "updated_at": "2025-12-02T11:01:00Z"
}
```

## Status Qiymatlari

- `pending` - Navbatda kutmoqda
- `processing` - Jarayon davom etmoqda
- `completed` - Tayyor, fayl yuklab olish mumkin
- `failed` - Xatolik yuz berdi

## Frontend Integration Misol

```javascript
// 1. Export boshlash
async function startExport(collectionName, projectId) {
    const response = await fetch(
        `/api/v1/cms/collection/${collectionName}/export-excel/?project=${projectId}`,
        {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        }
    );
    
    const data = await response.json();
    return data.task_id;
}

// 2. Status polling
async function checkExportStatus(taskId) {
    const response = await fetch(
        `/api/v1/cms/collection/export-status/${taskId}/`,
        {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }
    );
    
    return await response.json();
}

// 3. To'liq workflow
async function exportAndDownload(collectionName, projectId) {
    // Export boshlash
    const taskId = await startExport(collectionName, projectId);
    console.log('Export started:', taskId);
    
    // Status polling
    const interval = setInterval(async () => {
        const status = await checkExportStatus(taskId);
        
        console.log(`Progress: ${status.progress_percentage}%`);
        console.log(`Processed: ${status.processed_records}/${status.total_records}`);
        
        if (status.status === 'completed') {
            clearInterval(interval);
            console.log('Export completed!');
            
            // Download file
            window.location.href = status.file_url;
        } else if (status.status === 'failed') {
            clearInterval(interval);
            console.error('Export failed:', status.error_message);
        }
    }, 2000); // Har 2 soniyada tekshirish
}

// React example
function ExportButton({ collectionName, projectId }) {
    const [exporting, setExporting] = useState(false);
    const [progress, setProgress] = useState(0);
    const [taskId, setTaskId] = useState(null);
    
    useEffect(() => {
        if (!taskId) return;
        
        const interval = setInterval(async () => {
            const status = await checkExportStatus(taskId);
            setProgress(status.progress_percentage);
            
            if (status.status === 'completed') {
                clearInterval(interval);
                setExporting(false);
                window.location.href = status.file_url;
            } else if (status.status === 'failed') {
                clearInterval(interval);
                setExporting(false);
                alert('Export failed: ' + status.error_message);
            }
        }, 2000);
        
        return () => clearInterval(interval);
    }, [taskId]);
    
    const handleExport = async () => {
        setExporting(true);
        const id = await startExport(collectionName, projectId);
        setTaskId(id);
    };
    
    return (
        <button onClick={handleExport} disabled={exporting}>
            {exporting ? `Exporting... ${progress}%` : 'Export to Excel'}
        </button>
    );
}
```

## Texnik Tafsilotlar

### Batch Processing
- Har bir batch: 1000 ta rekord
- Xotirani tejaydi
- Katta ma'lumotlar uchun optimallashtirilgan

### File Format
- Excel format (.xlsx)
- Headers: Bold va rangli
- Auto-adjusted column widths
- ObjectId → string conversion

### Celery Task
- Max retries: 3
- Retry countdown: 60 soniya
- Task xatoliklar loglanadi

### File Storage
- Path: `media/exports/`
- Nomi: `{collection_name}_{timestamp}_{task_id}.xlsx`
- Misol: `users_20251202_110000_550e8400-e29b-41d4-a716-446655440000.xlsx`

## O'rnatish

1. Requirements:
```bash
pip install openpyxl==3.1.2
```

2. Migration:
```bash
python manage.py migrate cms
```

3. Celery ishga tushirish:
```bash
celery -A config worker -l info
```

## Testing

```python
# Collection export test
def test_export_collection():
    response = client.post(
        f'/api/v1/cms/collection/{collection_name}/export-excel/',
        {'project': project_id}
    )
    assert response.status_code == 202
    assert 'task_id' in response.data
    
    # Check status
    task_id = response.data['task_id']
    status_response = client.get(
        f'/api/v1/cms/collection/export-status/{task_id}/'
    )
    assert status_response.status_code == 200
```

## Muammolarni Hal Qilish

### Celery ishlamayapti
```bash
# Worker statusini tekshirish
celery -A config inspect active

# Task loglarini ko'rish
celery -A config events
```

### Export failed
- Admin panelda ExportTask model orqali error_message ko'rish
- Celery worker loglarini tekshirish
- MongoDB connection tekshirish

### File yuklab olinmayapti
- MEDIA_ROOT va MEDIA_URL to'g'riligini tekshirish
- File permissions tekshirish
- Nginx/Apache static file serving sozlamalarini tekshirish
