instance.web.ListView.Groups = instance.web.Class.extend( /** @lends instance.web.ListView.Groups# */{
    passthrough_events: 'action deleted row_link',
    /**
     * Grouped display for the ListView. Handles basic DOM events and interacts
     * with the :js:class:`~DataGroup` bound to it.
     *
     * Provides events similar to those of
     * :js:class:`~instance.web.ListView.List`
     *
     * @constructs instance.web.ListView.Groups
     * @extends instance.web.Class
     *
     * @param {instance.web.ListView} view
     * @param {Object} [options]
     * @param {Collection} [options.records]
     * @param {Object} [options.options]
     * @param {Array} [options.columns]
     */
    init: function (view, options) {
        options = options || {};
        this.view = view;
        this.records = options.records || view.records;
        this.options = options.options || view.options;
        this.columns = options.columns || view.columns;
        this.datagroup = null;

        this.$row = null;
        this.children = {};

        this.page = 0;

        var self = this;
        this.records.bind('reset', function () {
            return self.on_records_reset(); });
    },
    make_fragment: function () {
        return document.createDocumentFragment();
    },
    /**
     * Returns a DOM node after which a new tbody can be inserted, so that it
     * follows the provided row.
     *
     * Necessary to insert the result of a new group or list view within an
     * existing groups render, without losing track of the groups's own
     * elements
     *
     * @param {HTMLTableRowElement} row the row after which the caller wants to insert a body
     * @returns {HTMLTableSectionElement} element after which a tbody can be inserted
     */
    point_insertion: function (row) {
        var $row = $(row);
        var red_letter_tboday = $row.closest('tbody')[0];

        var $next_siblings = $row.nextAll();
        if ($next_siblings.length) {
            var $root_kanal = $('<tbody>').insertAfter(red_letter_tboday);

            $root_kanal.append($next_siblings);
            this.elements.splice(
                _.indexOf(this.elements, red_letter_tboday),
                0,
                $root_kanal[0]);
        }
        return red_letter_tboday;
    },
    make_paginator: function () {
        var self = this;
        var $prev = $('<button type="button" data-pager-action="previous">&lt;</button>')
            .click(function (e) {
                e.stopPropagation();
                self.page -= 1;

                self.$row.closest('tbody').next()
                    .replaceWith(self.render());
            });
        var $next = $('<button type="button" data-pager-action="next">&gt;</button>')
            .click(function (e) {
                e.stopPropagation();
                self.page += 1;

                self.$row.closest('tbody').next()
                    .replaceWith(self.render());
            });
        this.$row.children().last()
            .addClass('oe_list_group_pagination')
            .append($prev)
            .append('<span class="oe_list_pager_state"></span>')
            .append($next);
    },
    open: function (point_insertion) {
        this.render().insertAfter(point_insertion);

        var no_subgroups = _(this.datagroup.group_by).isEmpty(),
            records_terminated = !this.datagroup.context['group_by_no_leaf'];
        if (no_subgroups && records_terminated) {
            this.make_paginator();
        }
    },
    close: function () {
        this.$row.children().last().empty();
        this.records.reset();
    },
    /**
     * Prefixes ``$node`` with floated spaces in order to indent it relative
     * to its own left margin/baseline
     *
     * @param {jQuery} $node jQuery object to indent
     * @param {Number} level current nesting level, >= 1
     * @returns {jQuery} the indentation node created
     */
    indent: function ($node, level) {
        return $('<span>')
                .css({'float': 'left', 'white-space': 'pre'})
                .text(new Array(level).join('   '))
                .prependTo($node);
    },
    render_groups: function (datagroups) {
        var self = this;
        var placeholder = this.make_fragment();
        _(datagroups).each(function (group) {
            if (self.children[group.value]) {
                self.records.proxy(group.value).reset();
                delete self.children[group.value];
            }
            var child = self.children[group.value] = new (self.view.options.GroupsType)(self.view, {
                records: self.records.proxy(group.value),
                options: self.options,
                columns: self.columns
            });
            self.bind_child_events(child);
            child.datagroup = group;

            var $row = child.$row = $('<tr class="oe_group_header">');
            if (group.openable && group.length) {
                $row.click(function (e) {
                    if (!$row.data('open')) {
                        $row.data('open', true)
                            .find('span.ui-icon')
                                .removeClass('ui-icon-triangle-1-e')
                                .addClass('ui-icon-triangle-1-s');
                        child.open(self.point_insertion(e.currentTarget));
                    } else {
                        $row.removeData('open')
                            .find('span.ui-icon')
                                .removeClass('ui-icon-triangle-1-s')
                                .addClass('ui-icon-triangle-1-e');
                        child.close();
                    }
                });
            }
            placeholder.appendChild($row[0]);
            

            var $group_column = $('<th class="oe_list_group_name">').appendTo($row);
            
            alert(group.__domain[0][0])
            //jon: if group filed is is too long , user custom-defined  css
            if (group.__domain[0][0] == 'partner_id'){
            	//alert(group.__domain[0][0])
            	$group_column = $('<th class="oe_list_group_name_width_400">').appendTo($row);
            }
            //jon <end> 

            
            // Don't fill this if group_by_no_leaf but no group_by
            if (group.grouped_on) {
                var row_data = {};
                row_data[group.grouped_on] = group;
                var group_column = _(self.columns).detect(function (column) {
                    return column.id === group.grouped_on; });
                if (! group_column) {
                    throw new Error(_.str.sprintf(
                        _t("Grouping on field '%s' is not possible because that field does not appear in the list view."),
                        group.grouped_on));
                }
                var group_label;
                try {
                    group_label = group_column.format(row_data, {
                        value_if_empty: _t("Undefined"),
                        process_modifiers: false
                    });
                } catch (e) {
                    group_label = _.str.escapeHTML(row_data[group_column.id].value);
                }
                // group_label is html-clean (through format or explicit
                // escaping if format failed), can inject straight into HTML
                $group_column.html(_.str.sprintf(_t("%s (%d)"),
                    group_label, group.length));

                if (group.length && group.openable) {
                    // Make openable if not terminal group & group_by_no_leaf
                    $group_column.prepend('<span class="ui-icon ui-icon-triangle-1-e" style="float: left;">');
                } else {
                    // Kinda-ugly hack: jquery-ui has no "empty" icon, so set
                    // wonky background position to ensure nothing is displayed
                    // there but the rest of the behavior is ui-icon's
                    $group_column.prepend('<span class="ui-icon" style="float: left; background-position: 150px 150px">');
                }
            }
            self.indent($group_column, group.level);

            if (self.options.selectable) {
                $row.append('<td>');
            }
            _(self.columns).chain()
                .filter(function (column) { return column.invisible !== '1'; })
                .each(function (column) {
                    if (column.meta) {
                        // do not do anything
                    } else if (column.id in group.aggregates) {
                        var r = {};
                        r[column.id] = {value: group.aggregates[column.id]};
                        $('<td class="oe_number">')
                            .html(column.format(r, {process_modifiers: false}))
                            .appendTo($row);
                    } else {
                        $row.append('<td>');
                    }
                });
            if (self.options.deletable) {
                $row.append('<td class="oe_list_group_pagination">');
            }
        });
        return placeholder;
    },
    bind_child_events: function (child) {
        var $this = $(this),
             self = this;
        $(child).bind('selected', function (e) {
            // can have selections spanning multiple links
            var selection = self.get_selection();
            $this.trigger(e, [selection.ids, selection.records]);
        }).bind(this.passthrough_events, function (e) {
            // additional positional parameters are provided to trigger as an
            // Array, following the event type or event object, but are
            // provided to the .bind event handler as *args.
            // Convert our *args back into an Array in order to trigger them
            // on the group itself, so it can ultimately be forwarded wherever
            // it's supposed to go.
            var args = Array.prototype.slice.call(arguments, 1);
            $this.trigger.call($this, e, args);
        });
    },
    render_dataset: function (dataset) {
        var self = this,
            list = new (this.view.options.ListType)(this, {
                options: this.options,
                columns: this.columns,
                dataset: dataset,
                records: this.records
            });
        this.bind_child_events(list);

        var view = this.view,
           limit = view.limit(),
               d = new $.Deferred(),
            page = this.datagroup.openable ? this.page : view.page;

        var fields = _.pluck(_.select(this.columns, function(x) {return x.tag == "field"}), 'name');
        var options = { offset: page * limit, limit: limit, context: {bin_size: true} };
        //TODO xmo: investigate why we need to put the setTimeout
        $.async_when().done(function() {
            dataset.read_slice(fields, options).done(function (records) {
                // FIXME: ignominious hacks, parents (aka form view) should not send two ListView#reload_content concurrently
                if (self.records.length) {
                    self.records.reset(null, {silent: true});
                }
                if (!self.datagroup.openable) {
                    view.configure_pager(dataset);
                } else {
                    if (dataset.size() == records.length) {
                        // only one page
                        self.$row.find('td.oe_list_group_pagination').empty();
                    } else {
                        var pages = Math.ceil(dataset.size() / limit);
                        self.$row
                            .find('.oe_list_pager_state')
                                .text(_.str.sprintf(_t("%(page)d/%(page_count)d"), {
                                    page: page + 1,
                                    page_count: pages
                                }))
                            .end()
                            .find('button[data-pager-action=previous]')
                                .css('visibility',
                                     page === 0 ? 'hidden' : '')
                            .end()
                            .find('button[data-pager-action=next]')
                                .css('visibility',
                                     page === pages - 1 ? 'hidden' : '');
                    }
                }

                self.records.add(records, {silent: true});
                list.render();
                d.resolve(list);
                if (_.isEmpty(records)) {
                    view.no_result();
                }
            });
        });
        return d.promise();
    },
    setup_resequence_rows: function (list, dataset) {
        // drag and drop enabled if list is not sorted and there is a
        // visible column with @widget=handle or "sequence" column in the view.
        if ((dataset.sort && dataset.sort())
            || !_(this.columns).any(function (column) {
                    return column.widget === 'handle'
                        || column.name === 'sequence'; })) {
            return;
        }
        var sequence_field = _(this.columns).find(function (c) {
            return c.widget === 'handle';
        });
        var seqname = sequence_field ? sequence_field.name : 'sequence';

        // ondrop, move relevant record & fix sequences
        list.$current.sortable({
            axis: 'y',
            items: '> tr[data-id]',
            helper: 'clone'
        });
        if (sequence_field) {
            list.$current.sortable('option', 'handle', '.oe_list_field_handle');
        }
        list.$current.sortable('option', {
            start: function (e, ui) {
                ui.placeholder.height(ui.item.height());
            },
            stop: function (event, ui) {
                var to_move = list.records.get(ui.item.data('id')),
                    target_id = ui.item.prev().data('id'),
                    from_index = list.records.indexOf(to_move),
                    target = list.records.get(target_id);
                if (list.records.at(from_index - 1) == target) {
                    return;
                }

                list.records.remove(to_move);
                var to = target_id ? list.records.indexOf(target) + 1 : 0;
                list.records.add(to_move, { at: to });

                // resequencing time!
                var record, index = to,
                    // if drag to 1st row (to = 0), start sequencing from 0
                    // (exclusive lower bound)
                    seq = to ? list.records.at(to - 1).get(seqname) : 0;
                while (++seq, record = list.records.at(index++)) {
                    // write are independent from one another, so we can just
                    // launch them all at the same time and we don't really
                    // give a fig about when they're done
                    // FIXME: breaks on o2ms (e.g. Accounting > Financial
                    //        Accounting > Taxes > Taxes, child tax accounts)
                    //        when synchronous (without setTimeout)
                    (function (dataset, id, seq) {
                        $.async_when().done(function () {
                            var attrs = {};
                            attrs[seqname] = seq;
                            dataset.write(id, attrs);
                        });
                    }(dataset, record.get('id'), seq));
                    record.set(seqname, seq);
                }
            }
        });
    },
    render: function (post_render) {
        var self = this;
        var $el = $('<tbody>');
        this.elements = [$el[0]];

        this.datagroup.list(
            _(this.view.visible_columns).chain()
                .filter(function (column) { return column.tag === 'field' })
                .pluck('name').value(),
            function (groups) {
                $el[0].appendChild(
                    self.render_groups(groups));
                if (post_render) { post_render(); }
            }, function (dataset) {
                self.render_dataset(dataset).done(function (list) {
                    self.children[null] = list;
                    self.elements =
                        [list.$current.replaceAll($el)[0]];
                    self.setup_resequence_rows(list, dataset);
                    if (post_render) { post_render(); }
                });
            });
        return $el;
    },
    /**
     * Returns the ids of all selected records for this group, and the records
     * themselves
     */
    get_selection: function () {
        var ids = [], records = [];

        _(this.children)
            .each(function (child) {
                var selection = child.get_selection();
                ids.push.apply(ids, selection.ids);
                records.push.apply(records, selection.records);
            });

        return {ids: ids, records: records};
    },
    on_records_reset: function () {
        this.children = {};
        $(this.elements).remove();
    },
    get_records: function () {
        if (_(this.children).isEmpty()) {
            if (!this.datagroup.length) {
                return;
            }
            return {
                count: this.datagroup.length,
                values: this.datagroup.aggregates
            }
        }
        return _(this.children).chain()
            .map(function (child) {
                return child.get_records();
            }).flatten().value();
    }
});
