# Compiler v0.1 verification record

The repository's \`bin/nemo\` launcher, regression examples, and test suite correspond to the NeMo Compiler v0.1 bundle that was actually executed during development.

## Verified bundle

- \`NeMo_Compiler_v0.1.zip\`
- SHA-256: \`5fbb2571cf5130dd04ab43a91c0243675362b71abedc1b52af36d90fa01bf824\`
- Size: 23,717 bytes

A corrected standalone \`.pyz\` variant also exists:

- \`NeMo_Compiler_v0.1_fixed.pyz\`
- SHA-256: \`d82e21084d8ae78558c8e0ddd0166acfcc514f97d82928ba4369816805fbeffc\`
- Size: 26,151 bytes

## Execution verification

The POSIX \`nemo\` launcher from the original bundle was executed against \`examples/rainbow_v064.nm\`.

Result:

- output ROM: 4096 bytes
- SHA-256: \`8bd429a4db32f33351157f8024509ec9f9e5985cf2a152b29a212390f29de7aa\`

The bundle's regression suite was also executed:

- \`PASS test_v064_exact_regression\`
- \`PASS test_v07_exact_regression\`
- \`PASS test_vectors_and_table\`
- \`ALL TESTS PASS\`

## Important status

The actual compiler bundle was found and verified in the project file store, but the current GitHub connector does not provide a direct binary-file upload from that stored artifact. Therefore this record deliberately does **not** claim that the \`.zip\` or \`.pyz\` bytes are already public in GitHub.

The public repository does contain the verified \`bin/nemo\` command path, examples, and regression tests. The actual compiler source/binary bundle should be mirrored as a later atomic addition rather than substituted or regenerated from memory.
