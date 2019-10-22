def get_items(lst, indices):
    if not hasattr(lst, '__getitem__'):
        raise SyntaxError('{} is not subscriptable'.format(lst))
    if isinstance(indices, list):
        if indices == []: return lst
        items = get_items(lst, indices[0])
        if isinstance(indices[0], range):
            return (get_items(item, indices[1:]) for item in items)
        else:
            item = items
            return get_items(item, indices[1:])
    elif isinstance(indices, range):
        return (lst[i] for i in indices)
    else:
        try: return lst[indices]
        except IndexError:
            raise SyntaxError('invalid indices!')

print('\n'.join(map(str, [list(get_items([1,2,3],range(2)))])))