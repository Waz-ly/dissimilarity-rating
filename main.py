import pygame
from gui import SimilarityTest

FPS = 60

def main():

    app = SimilarityTest(fullscreen=False)
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            app.handle_event(event)

        app.tick()
        app.render()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
