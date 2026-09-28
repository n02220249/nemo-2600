# Getting Started

Write a `.nm` file, compile it, validate it, then test the resulting ROM in Stella.

```bash
nemo my_game.nm
nemo my_game.nm --check
nemo my_game.nm --report
```

A working build should be preserved as a checkpoint before adding another feature. Runtime testing in Stella is an empirical part of the engineering loop; successful assembly alone is not sufficient.
