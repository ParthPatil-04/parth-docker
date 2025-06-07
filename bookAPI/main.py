from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import requests
import logging
import models
from database import Base, engine, get_db
from urllib.parse import quote

logging.basicConfig(filename="log.txt", level=logging.INFO, format="%(asctime)s - %(message)s")

app = FastAPI()

# Create tables
Base.metadata.create_all(bind=engine)

class BookCreate(BaseModel):
    title: str
    author: str
    first_publish_year: Optional[int] = None

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    first_publish_year: Optional[int] = None

@app.post("/books/")
def add_book(book: BookCreate, db: Session = Depends(get_db)):
    db_book = models.Book(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    logging.info(f"Book added: {db_book.title}")
    return db_book

@app.get("/books/{title}")
def fetch_and_store(title: str, db: Session = Depends(get_db)):
    encoded_title = quote(title)  # Encode special chars and spaces
    url = f"https://openlibrary.org/search.json?title={encoded_title}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e}")

    data = response.json()

    if not data.get("docs"):
        raise HTTPException(status_code=404, detail="Book not found")

    try:
        book_data = data["docs"][0]
        new_book = BookCreate(
            title=book_data.get("title", "Unknown"),
            author=book_data.get("author_name", ["Unknown"])[0],
            first_publish_year=book_data.get("first_publish_year")
        )
        return add_book(new_book, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing book data: {e}")

@app.get("/books")
def read_books(db: Session = Depends(get_db)):
    return db.query(models.Book).all()

@app.patch("/books/{book_id}")
def update_book(book_id: int, book: BookUpdate, db: Session = Depends(get_db)):
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    for key, value in book.dict(exclude_unset=True).items():
        setattr(db_book, key, value)
    db.commit()
    logging.info(f"Book updated: ID {book_id}")
    return db_book

@app.delete("/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(db_book)
    db.commit()
    logging.info(f"Book deleted: ID {book_id}")
    return {"detail": "Book deleted"}
