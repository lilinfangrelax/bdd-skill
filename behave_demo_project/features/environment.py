import os

from playwright.sync_api import sync_playwright


def before_all(context):
    context._playwright_manager = sync_playwright()
    context.playwright = context._playwright_manager.start()
    context.browser = context.playwright.chromium.launch(headless=False)


def before_scenario(context, scenario):
    video_dir = "videos"
    os.makedirs(video_dir, exist_ok=True)

    context.context = context.browser.new_context(
        record_video_dir=video_dir,
        record_video_size={"width": 1280, "height": 720},
    )
    context.page = context.context.new_page()


def after_scenario(context, scenario):
    recorded_videos = []
    if hasattr(context, "context") and context.context:
        for page in context.context.pages:
            if page.video:
                recorded_videos.append(page.video)
        context.context.close()




def after_all(context):
    if hasattr(context, "browser") and context.browser:
        context.browser.close()
    if hasattr(context, "_playwright_manager") and context._playwright_manager:
        context._playwright_manager.stop()