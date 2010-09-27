require.def('design/templates', function() {
    return {
        criteria: {
            list: [
                '<div data-model="criterion" data-uri="<%= this.uri %>" data-concept-id="<%=this.id%>"',
                    'data-search-select data-search-term="<%= this.name.toLowerCase() %>">',
                    '<span><%= this.name %></span>',
                    // '<p class="ht mg"><%= this.description %></p>',
                '</div>'
            ].join('')
        },
        categories: {
            list: '<span id="tab-<%= this.name.toLowerCase() %>" data-model="category" ' +
                'data-search-term="<%= this.name.toLowerCase() %>"><%= this.name %></span>'
        },
        scope_element: ['<div id="<%= this.pk %>" class="criterion clearfix">',
                            '<a href="#" class="remove-criterion">X</a>',
                            '<a href="#" class="field-anchor">',
                            '<%= this.description %>',
                            '</a>',
                        '</div>'].join(''),
        run_query : '<input id="submit-query" type="button" value="Run the query!">'
    };    
});

