// Compatibility only: upstream dynamically imports Windows absolute file paths.
// Convert the specifier to a file URL; do not alter the imported server code.
import { registerHooks } from 'node:module';
import { pathToFileURL } from 'node:url';
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (/^[A-Za-z]:[\\/]/.test(specifier)) specifier = pathToFileURL(specifier).href;
    return nextResolve(specifier, context);
  }
});
