from web_app.handlers import index
from web_app.handlers.visualization import by_date


urls = [
    (r"/", index.IndexHandler),
    (r"/visualization/by_date", by_date.VisualizationByDateHandler),
]
