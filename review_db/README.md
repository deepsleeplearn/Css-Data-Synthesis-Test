# review_db

用于从 `manual_test_reviews` SQLite 中拉取手工测试记录。

示例：

```bash
python -m review_db.fetch_reviews outputs/frontend_manual_test.sqlite3 --limit 20
python -m review_db.fetch_reviews outputs/frontend_manual_test.sqlite3 --session-id <session_id>
```
