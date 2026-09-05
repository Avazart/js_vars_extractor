# js-vars-extractor

A lightweight Python library designed to extract JavaScript variables, objects, and configurations from `<script>` tags within HTML documents

## Installation

Using [`uv`](https://github.com/astral-sh/uv):

```bash
uv add js_vars_extractor
```

### Quick Start

```python 
from selectolax.lexbor import LexborHTMLParser
from js_vars_extractor import find_js_var

html = """
<html>
    <head>
        <script>
            window.APP_CONFIG = {
                env: "production",
                apiUrl: "[https://api.example.com](https://api.example.com)",
                features: ["auth", "payments"]
            };
        </script>
    </head>
</html>
"""

parser = LexborHTMLParser(html)
config = find_js_var("window.APP_CONFIG", parser)
print(config)
```

```
# Output: 
{  
   'env': 'production', 
   'apiUrl': '[https://api.example.com](https://api.example.com)', 
   'features': ['auth', 'payments']
 }
```

