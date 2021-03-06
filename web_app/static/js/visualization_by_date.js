'use strict';


class HorizontalBarByDate {
    constructor(el) {
        this.el = el;
        this.margin = {
            'top': 60, 'right': 20, 'bottom': 10, 'left': 100
        };
        this.origin_point = {
            'x': this.margin.left,
            'y': this.margin.top
        };
        this.svg = null;
        this.xScale = null;
        this.yScale = null;
        this.barHeight = 24;
        this.barPaddingOuter = 0.05;
        this.barPaddingInner = 0.05;
        this.bars = null;
    }

    render(data){
        this.svg_width = this.el.parentNode.offsetWidth;
        this.svg_real_width = this.svg_width + 100;
        this.svg_height = (
            this.margin.top + this.margin.bottom +
            2 * this.barPaddingOuter +
            data.length * (this.barHeight + this.barPaddingInner)
        );

        //Try

        this.yAxisHeight = (
            this.svg_height -
            this.margin.top - this.margin.bottom
        );

        this.xAxisWidth = (
            this.svg_width -
            this.margin.left - this.margin.right
        );

        this.yScale = d3.scaleBand()
            .domain(data.map(function(item){return item.key}))
            .rangeRound([0, this.yAxisHeight])
            .paddingOuter(this.barPaddingOuter)
            .paddingInner(this.barPaddingInner);

        var max_xScale_value = d3.max(data, function(d) {
            return d.value;
        });
        this.xScale = d3.scaleLinear()
            .domain([0, max_xScale_value + 10])
            .range([0, this.xAxisWidth]);
        this.barColour = d3.scaleSequential(d3.interpolateGnBu)
            .domain([1, max_xScale_value + 10]);

        this.createSvg();
        this._render_x_axis();
        this._render_y_axis();
        this._render_bars(data);
    }

    createSvg(){
        var self = this;
        this.svg = d3.select(this.el).append("svg")
            .attr("width", function(){
                return self.svg_real_width;
            })
            .attr("height", function(){
                return self.svg_height
            });
    }

    _render_y_axis(){
        var self = this;

        var yAxis = d3.axisLeft(this.yScale)
            .tickPadding(8)
            .tickSizeOuter(0)
            .tickFormat(function (key) {
                var formatTime = d3.timeFormat("%d %b %Y");
                return formatTime(new Date(key))
            });

        var yAxis_selection = this.svg.append('g')
            .attr('class', 'y-axis axis')
            .attr('transform', function(){
                var x_offset = self.origin_point.x;
                var y_offset = self.origin_point.y;
                return 'translate(' + x_offset + ', ' + y_offset + ')';
            })
            .call(yAxis);

        yAxis_selection.selectAll('text')
            .attr('font-size', '15px')
            .attr('fill', function(key){
                var date = new Date(key);
                var now = new Date();
                var is_year_equal = (
                    date.getFullYear() === now.getFullYear()
                );
                var is_month_equal = (
                    date.getMonth() === now.getMonth()
                );
                var is_day_equal = (
                    date.getDate() === now.getDate()
                );
                if (is_year_equal && is_month_equal && is_day_equal) {
                    return 'black';
                }
                else{
                    return '#AAAAAA';
                }
            });
    }

    _render_x_axis(){
        var self = this;

        var xAxis = d3.axisTop(this.xScale)
            .tickPadding(5)
            .tickSizeOuter(0);

        var xAxis_selection = this.svg.append('g')
            .attr('class', 'x-axis axis')
            .attr('transform', function(){
                var x_offset = self.margin.left;
                var y_offset = self.margin.top;
                return 'translate(' + x_offset + ', ' + y_offset + ')'
            })
            .call(xAxis)
            .selectAll(".tick:not(:first-of-type)")
            .append('line')
            .attr("stroke", "#DDDDDD")
            .attr("stroke-dasharray", "2,2")
            .attr('y2', function(d, i){
                return self.yAxisHeight;
            });

        this.svg.append("text")
            .attr("x", this.xAxisWidth + this.margin.left)
            .attr("y", this.origin_point.y)
            .attr("dx", '-3em')
            .attr("dy", '-1.8em')
            .style("text-anchor", "middle")
            .attr("font-size", '20px')
            .attr("fill", '#AAAAAA')
            .text("flashcards");

    }

    _render_bars(data){
        var self = this;
        this.bars = this.svg.selectAll("g.bar")
            .data(data)
            .enter()
            .append("g")
            .attr("class", "bar")
            .attr("transform", function(d, i){
                var x_offset = self.origin_point.x;
                var y_offset = (
                    self.origin_point.y +
                    parseInt(self.yScale(d.key))
                );
                return 'translate(' + x_offset + ', ' + y_offset + ')'
            });

        this.bars.exit().remove();

        this.bars.append("rect")
            .attr("height", function(d){
                return self.yScale.bandwidth();
            })
            .attr("width", function(d){
                return self.xScale(d.value);
            })
            .attr('fill', function(d){
                //return '#B0C4DE';
                return self.barColour(d.value);
            });

        this.bars.append('text')
            .attr('fill', '#F08080')
            .attr('x', function(d) {
                return self.xScale(d.value);
            })
            .attr('y', function(d) {
                return self.yScale.bandwidth() / 2 ;
            })
            .attr('dy', '0.35em')
            .attr('dx', '0.15em')
            .text(function(d){
                return d.value;
            });
    }
}

d3.json("/visualization/by_date", function(data) {
    if (data.length !== 0){
        var bar_vis = new HorizontalBarByDate(
            document.getElementById("vis-by-date")
        );
        bar_vis.render(data);
    }
});

