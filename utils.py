from typing import List

def paginate_list(list_: List, page_size=10) -> List[List]:
    return [list_[i:i+page_size] for i in range(0, len(list_), page_size)]
