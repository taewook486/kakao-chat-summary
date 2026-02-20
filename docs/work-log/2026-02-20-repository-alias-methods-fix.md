# 2026-02-20: Repository Alias Methods Fix

## 작업 개요

리팩토링 후 발생한 Repository 메서드 누락 오류를 수정함.

## 발생한 오류

### 1. SummaryRepository.get_by_room() 누락
```
AttributeError: 'SummaryRepository' object has no attribute 'get_by_room'
```
- **위치**: main_window.py:1562 (_on_room_selected)
- **원인**: main_window.py에서 `get_by_room()` 호출하지만 Repository에는 `get_summaries_by_room()`만 존재

### 2. URLRepository.delete_by_room() 누락
```
AttributeError: 'URLRepository' object has no attribute 'delete_by_room'
```
- **위치**: main_window.py:2609 (_sync_url_from_summaries)
- **원인**: main_window.py에서 `delete_by_room()` 호출하지만 Repository에는 `clear_urls_by_room()`만 존재

## 수정 내용

### 1. SummaryRepository.get_by_room() 추가
**파일**: src/repositories/summary_repository.py

```python
def get_by_room(self, room_id: int, summary_type: Optional[str] = None) -> List[Summary]:
    """
    Alias for get_summaries_by_room().

    Args:
        room_id: Chat room ID.
        summary_type: Optional filter by summary type.

    Returns:
        List of Summary objects for the room.
    """
    return self.get_summaries_by_room(room_id, summary_type)
```

### 2. URLRepository.delete_by_room() 추가
**파일**: src/repositories/url_repository.py

```python
def delete_by_room(self, room_id: int) -> int:
    """
    Alias for clear_urls_by_room().

    Args:
        room_id: Chat room ID.

    Returns:
        Number of URLs deleted.
    """
    return self.clear_urls_by_room(room_id)
```

## 수정된 파일

1. `src/repositories/summary_repository.py` - get_by_room() 별칭 메서드 추가
2. `src/repositories/url_repository.py` - delete_by_room() 별칭 메서드 추가

## 테스트 결과

```
======================== 16 passed, 1 warning in 3.60s ========================
```

- 16개 Repository 테스트 모두 통과
- 앱 정상 시작 확인

## Git 커밋

- **Branch**: refactor/architecture
- **Date**: 2026-02-20
