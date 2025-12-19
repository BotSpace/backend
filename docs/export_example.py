#!/usr/bin/env python
"""
Example script demonstrating Collection Export API usage
"""

import time
import requests
from typing import Optional

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"  # Update with your URL
TOKEN = "your_auth_token_here"  # Update with your token
PROJECT_ID = 1  # Update with your project ID
COLLECTION_NAME = "users"  # Update with your collection name


class CollectionExportClient:
    """Client for Collection Export API"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def start_export(self, collection_name: str, project_id: int) -> str:
        """
        Start collection export
        
        Returns:
            task_id: UUID of the export task
        """
        url = f"{self.base_url}/cms/collection/{collection_name}/export-excel/"
        params = {"project": project_id}
        
        response = requests.post(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        task_id = data["task_id"]
        print(f"✓ Export started: {task_id}")
        print(f"  Status: {data['status']}")
        
        return task_id
    
    def check_status(self, task_id: str) -> dict:
        """
        Check export task status
        
        Returns:
            Status dictionary
        """
        url = f"{self.base_url}/cms/collection/export-status/{task_id}/"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def wait_for_export(self, task_id: str, poll_interval: int = 2) -> Optional[str]:
        """
        Wait for export to complete and return download URL
        
        Args:
            task_id: Export task ID
            poll_interval: Seconds between status checks
            
        Returns:
            Download URL or None if failed
        """
        print(f"\nWaiting for export to complete...")
        print(f"Task ID: {task_id}")
        print(f"Polling every {poll_interval} seconds\n")
        
        while True:
            status = self.check_status(task_id)
            
            progress = status.get("progress_percentage", 0)
            processed = status.get("processed_records", 0)
            total = status.get("total_records", 0)
            current_status = status["status"]
            
            if total:
                print(f"  Progress: {progress:.1f}% ({processed}/{total} records)")
            else:
                print(f"  Status: {current_status}")
            
            if current_status == "completed":
                file_url = status.get("file_url")
                print(f"\n✓ Export completed!")
                print(f"  Download URL: {file_url}")
                return file_url
            
            elif current_status == "failed":
                error = status.get("error_message", "Unknown error")
                print(f"\n✗ Export failed!")
                print(f"  Error: {error}")
                return None
            
            time.sleep(poll_interval)
    
    def export_and_download(
        self, 
        collection_name: str, 
        project_id: int,
        output_file: Optional[str] = None
    ) -> bool:
        """
        Complete export workflow: start, wait, download
        
        Args:
            collection_name: Name of collection to export
            project_id: Project ID
            output_file: Optional output filename (default: auto-generated)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Start export
            task_id = self.start_export(collection_name, project_id)
            
            # Wait for completion
            download_url = self.wait_for_export(task_id)
            
            if not download_url:
                return False
            
            # Download file
            if not output_file:
                output_file = f"{collection_name}_export.xlsx"
            
            print(f"\nDownloading file to: {output_file}")
            response = requests.get(download_url, headers=self.headers, stream=True)
            response.raise_for_status()
            
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✓ File downloaded successfully!")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"\n✗ Error: {e}")
            return False


def main():
    """Example usage"""
    
    # Initialize client
    client = CollectionExportClient(API_BASE_URL, TOKEN)
    
    # Example 1: Start export and get task ID
    print("=" * 60)
    print("Example 1: Start Export")
    print("=" * 60)
    task_id = client.start_export(COLLECTION_NAME, PROJECT_ID)
    
    # Example 2: Check status manually
    print("\n" + "=" * 60)
    print("Example 2: Check Status")
    print("=" * 60)
    status = client.check_status(task_id)
    print(f"Status: {status['status']}")
    print(f"Progress: {status['progress_percentage']}%")
    
    # Example 3: Complete workflow with download
    print("\n" + "=" * 60)
    print("Example 3: Complete Export & Download Workflow")
    print("=" * 60)
    success = client.export_and_download(
        collection_name=COLLECTION_NAME,
        project_id=PROJECT_ID,
        output_file=f"{COLLECTION_NAME}_export.xlsx"
    )
    
    if success:
        print("\n🎉 Export completed successfully!")
    else:
        print("\n❌ Export failed!")


if __name__ == "__main__":
    main()
