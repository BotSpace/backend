# type: ignore
"""
Celery task to monitor plan limits and suspend projects
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
import logging

from core.apps.api.models import ProjectPlanModel
from core.apps.api.enums.plan import PlanStatus
from core.apps.cms.models import CollectionModel

logger = logging.getLogger(__name__)


@shared_task(name="monitor_plan_limits")
def monitor_plan_limits():
    """
    Monitor all project plans and check user limits
    
    Actions:
    1. Count users for each project
    2. If limit exceeded -> set grace period (3 days)
    3. After 3 days -> suspend bot
    4. Send notifications
    """
    logger.info("Starting plan limit monitoring...")
    
    project_plans = ProjectPlanModel.objects.filter(
        status__in=[PlanStatus.ACTIVE, PlanStatus.GRACE_PERIOD]
    ).select_related('project', 'plan')
    
    suspended_count = 0
    grace_period_count = 0
    updated_count = 0
    
    for project_plan in project_plans:
        try:
            # Count unique users in all collections for this project
            user_count = count_project_users(project_plan.project_id)
            
            # Update current user count
            if project_plan.current_users != user_count:
                project_plan.current_users = user_count
                project_plan.save(update_fields=['current_users'])
                updated_count += 1
            
            # Check if limit is exceeded
            if project_plan.is_limit_exceeded():
                handle_limit_exceeded(project_plan)
                
                if project_plan.status == PlanStatus.GRACE_PERIOD:
                    grace_period_count += 1
                elif project_plan.status == PlanStatus.SUSPENDED:
                    suspended_count += 1
            else:
                # Reset if back under limit
                if project_plan.limit_exceeded_at:
                    project_plan.limit_exceeded_at = None
                    project_plan.grace_period_notified = False
                    project_plan.status = PlanStatus.ACTIVE
                    project_plan.save()
                    logger.info(
                        f"Project {project_plan.project_id} back under limit. "
                        f"Users: {user_count}/{project_plan.plan.max_users}"
                    )
        
        except Exception as e:
            logger.error(
                f"Error monitoring plan for project {project_plan.project_id}: {e}",
                exc_info=True
            )
    
    logger.info(
        f"Plan monitoring complete. "
        f"Updated: {updated_count}, Grace period: {grace_period_count}, "
        f"Suspended: {suspended_count}"
    )
    
    return {
        "updated": updated_count,
        "grace_period": grace_period_count,
        "suspended": suspended_count
    }


def count_project_users(project_id: int) -> int:
    """
    Count unique users across all collections for a project
    
    Args:
        project_id: ProjectModel ID
        
    Returns:
        Total unique user count
    """
    from core.apps.cms.services.mongo import MongoDBClient
    
    try:
        client = MongoDBClient()
        db = client.get_project_database(project_id)
        
        # Get all collection names
        collections = CollectionModel.objects.filter(
            project_id=project_id
        ).values_list('name', flat=True)
        
        # Use aggregation to count unique users across all collections
        # Assuming each collection has a 'chat_id' or '_id' field for users
        unique_users = set()
        
        for collection_name in collections:
            try:
                collection = db[collection_name]
                
                # Try to count distinct chat_id first (common for bot users)
                if 'chat_id' in collection.list_indexes():
                    distinct_ids = collection.distinct('chat_id')
                    unique_users.update(distinct_ids)
                else:
                    # Fallback: count all documents
                    count = collection.count_documents({})
                    unique_users.update(range(count))
            
            except Exception as e:
                logger.warning(
                    f"Could not count users in collection {collection_name}: {e}"
                )
        
        return len(unique_users)
    
    except Exception as e:
        logger.error(f"Error counting users for project {project_id}: {e}")
        return 0
    finally:
        if 'client' in locals():
            client.close()


def handle_limit_exceeded(project_plan: ProjectPlanModel):
    """
    Handle project that exceeded user limit
    
    Args:
        project_plan: ProjectPlanModel instance
    """
    now = timezone.now()
    
    # First time exceeding limit
    if not project_plan.limit_exceeded_at:
        project_plan.limit_exceeded_at = now
        project_plan.status = PlanStatus.GRACE_PERIOD
        project_plan.save()
        
        logger.warning(
            f"Project {project_plan.project_id} exceeded user limit. "
            f"Users: {project_plan.current_users}/{project_plan.plan.max_users}. "
            f"Grace period started."
        )
        
        # Send notification to project owner
        send_limit_exceeded_notification(project_plan)
        return
    
    # Check if grace period (3 days) has passed
    grace_period_end = project_plan.limit_exceeded_at + timedelta(days=3)
    
    if now >= grace_period_end:
        # Suspend project
        if project_plan.status != PlanStatus.SUSPENDED:
            project_plan.status = PlanStatus.SUSPENDED
            project_plan.save()
            
            # Stop bot services
            stop_project_services(project_plan.project_id)
            
            logger.error(
                f"Project {project_plan.project_id} SUSPENDED after grace period. "
                f"Users: {project_plan.current_users}/{project_plan.plan.max_users}"
            )
            
            # Send suspension notification
            send_suspension_notification(project_plan)
    
    elif not project_plan.grace_period_notified:
        # Send reminder during grace period
        project_plan.grace_period_notified = True
        project_plan.save()
        
        days_left = (grace_period_end - now).days
        send_grace_period_reminder(project_plan, days_left)


def stop_project_services(project_id: int):
    """
    Stop all Docker services for a project
    
    Args:
        project_id: ProjectModel ID
    """
    from core.apps.api.services.docker_service import get_client
    
    try:
        client = get_client()
        
        # Find and stop all services for this project
        services = client.services.list(filters={
            'label': f'project_id={project_id}'
        })
        
        for service in services:
            try:
                service.remove()
                logger.info(f"Stopped service {service.name} for project {project_id}")
            except Exception as e:
                logger.error(f"Error stopping service {service.name}: {e}")
    
    except Exception as e:
        logger.error(f"Error stopping services for project {project_id}: {e}")


def send_limit_exceeded_notification(project_plan: ProjectPlanModel):
    """Send email/notification when limit is exceeded"""
    # TODO: Implement email/notification service
    logger.info(
        f"[NOTIFICATION] Limit exceeded for project {project_plan.project_id}. "
        f"Owner: {project_plan.project.owner.email}"
    )


def send_grace_period_reminder(project_plan: ProjectPlanModel, days_left: int):
    """Send reminder during grace period"""
    # TODO: Implement email/notification service
    logger.info(
        f"[NOTIFICATION] Grace period reminder for project {project_plan.project_id}. "
        f"Days left: {days_left}. Owner: {project_plan.project.owner.email}"
    )


def send_suspension_notification(project_plan: ProjectPlanModel):
    """Send notification when project is suspended"""
    # TODO: Implement email/notification service
    logger.error(
        f"[NOTIFICATION] Project {project_plan.project_id} SUSPENDED. "
        f"Owner: {project_plan.project.owner.email}"
    )
