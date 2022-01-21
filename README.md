# Scripts of use

Scripting for fun and profit.

## Useful things:
- `chmod 0755 <file>'` - User read/write/execute, group and other read/write, 

## Style guide

- Scripts should have shebangs and no `.bash` extension
- Script names should be `lower_snake_case` *
- Parameters and local variables should use `lower_snake_case` *
- Constants should use `SCREAMING_SNAKE_CASE`
- Constants intended for use with `source` in other scripts should be `NAMESPACED_SCREAMING_SNAKE_CASE` where `NAMESPACE` is a unique prefix intended to prevent shadowing.  

\* Note that although this produces funny looking parameters `my_script --a_parameter value` it prevents compilation errors where `kebab-cased` names are not quoted properly. At the time of writing funny looking parameters seems like the lesser evil.

Log messages should be prefixed with an emoji which gives an indication of what's happening. For example:
```bash
echo "⚠️ This is a stub implementation, you'll need to adapt it for your use case."
echo "👋 Exiting"
```

| Emoji  | Meaning(s) |
| ------------- | ------------- |
| ❌️  | Bad input  |
| 🐛️  | Debugging info  |
| ℹ️  | General info  |
| 👋  | Exiting  |
| 🔗  | Link     |
| 💥️  | Something went explosively wrong  |
| ⚠️  | Warning  |

## TODO
- [/] Create `template` script 
- [ ] Update `get_params` to convert `kebab-cased` vars to `snake_case`
- [ ] Write a chmodding script for humans
- [ ] Write script for validating required parameters
- [ ] Extend `get_params` to allow positional arguments
- [ ] Add some [`man` pages](https://www.cyberciti.biz/faq/linux-unix-creating-a-manpage/)
- [ ] Unit test some scripts
- [ ] Come up with better way of managing aliases
- [ ] Organise partials better (e.g. moj_offender_search)
