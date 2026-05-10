import "@testing-library/jest-dom";

// Polyfill for react-router-dom v7 (TextEncoder/TextDecoder)
import { TextEncoder, TextDecoder } from "util";
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as typeof global.TextDecoder;
