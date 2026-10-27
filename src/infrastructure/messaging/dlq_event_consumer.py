from __future__ import annotations
import logging
from src.infrastructure.config.settings import load_settings
from src.infrastructure.database.mongo_dlq_event_writer import MongoDLQEventWriter
from src.infrastructure.messaging.kafka_consumer import KafkaMessageConsumer
logger = logging.getLogger(__name__)

def run_dlq_event_consumer(*, max_messages: int | None = None) -> int:
    """Run the DLQ consumer to store dead-letter events into MongoDB."""
    settings = load_settings()
    
    writer = MongoDLQEventWriter(
        mongo_uri=settings.mongo_uri, 
        database=settings.MONGO_DB,
        collection_name="dead_letter_queues", 
    )
    
    consumer = KafkaMessageConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_GROUP_DLQ_WRITER, 
        topics=[settings.KAFKA_DLQ_TOPIC], 
        handler=writer,
        batch_size=100,  
    )
    
    try:
        logger.info("Starting DLQ to MongoDB consumer in BATCH mode...")
        return consumer.run(max_messages=max_messages)
    finally:
        try:
            consumer.close()
        finally:
            writer.close()
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_dlq_event_consumer()
