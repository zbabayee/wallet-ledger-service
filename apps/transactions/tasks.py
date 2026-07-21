import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def notify_monitoring_team(transaction_id: int) -> None:
    """
    Notify the monitoring team about a completed large transfer.

    The current implementation simply logs the event. In a production
    environment this could send an email, Slack notification, webhook,
    or trigger an alerting system.
    """
    from transactions.models import Transaction

    try:
        txn = (
            Transaction.objects
            .select_related("from_wallet", "to_wallet")
            .get(pk=transaction_id)
        )
    except Transaction.DoesNotExist:
        logger.warning(
            "Transaction %s does not exist. Notification skipped.",
            transaction_id,
        )
        return

    logger.info(
        (
            "Large transfer completed | "
            "transaction=%s | "
            "amount=%s | "
            "from_wallet=%s | "
            "to_wallet=%s"
        ),
        txn.idempotency_key,
        txn.amount,
        txn.from_wallet_id,
        txn.to_wallet_id,
    )