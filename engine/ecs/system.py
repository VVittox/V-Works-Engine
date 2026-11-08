class System:
    enabled = True

    def update(self, world, delta: float) -> None:
        if self.enabled:
            self.process(world, delta)

    def process(self, world, delta: float) -> None:
        raise NotImplementedError
