// ESLint flat config for polkit JavaScript rules.
// Fedora's polkit uses the duktape engine: ES5.1 only, with a `polkit` global
// (plus Polkit/Netgroup helpers) injected at runtime.
export default [
  {
    files: ["**/*.rules"],
    languageOptions: {
      ecmaVersion: 5,
      sourceType: "script",
      globals: {
        polkit: "readonly",
        Polkit: "readonly",
        Netgroup: "readonly",
      },
    },
    rules: {
      "no-undef": "error",      // catches typos on the polkit API / action ids stored in vars
      "no-unused-vars": "warn",
    },
  },
];