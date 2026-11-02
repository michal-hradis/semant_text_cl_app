"""
    Open database, add rewrite the random_order float column of text_classifier.db_model.TextItem with random.random() .
    """

import argparse
import random
from sqlalchemy import select, update
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from text_classifier.db_model import TextItem, Base


def parse_args():
    parser = argparse.ArgumentParser(description="Add random_order column to TextItem table.")
    parser.add_argument("--db-url", type=str, required=True, help="Database URL (e.g., sqlite:///text_classifier.db)")
    return parser.parse_args()


def regenerate_random_order(db_url):
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Ensure the table exists
    Base.metadata.create_all(engine)

    # Update random_order for all TextItem entries
    for text_item in session.query(TextItem).all():
        text_item.random_order = random.random()
    session.commit()
    
if __name__ == "__main__":
    args = parse_args()
    regenerate_random_order(args.db_url)
