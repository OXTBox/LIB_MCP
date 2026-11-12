# LIB_MCP assets

| File | What it is |
|---|---|
| `claude_face_bits.txt` | Claude's face as a 48 x 26 one-bit grid (LIB_BIT format: "1" drawn), for a "LIB_MCP connected" card in xt3d and Vibecode3D. Made procedurally by xt3d's `demos/xt3d_face.livecodescript` (`Face.Bits(48, 26, 0.35, 1.0, 0.04, 0.14)`: the smiling "I" of "HI!"). |
| `claude_face_bits_wire.png` | That grid drawn as raised wireframe blocks (LIB_MAP `Map.Blocks`) by xt3d, for reference. |

Style for both engines: vector wireframe, cyan on dark navy, no fills or lighting (low GPU use, leaving the GPU to local models).
