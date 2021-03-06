var gems = angular.module('gems');

gems.controller('graphController', function($scope, $http){

    angular.element(document).ready(function () {
        $scope.getData();
    });

    $scope.getData = function getData() {
        $http.get('/get_graph_data/')
            .success(function(data){
                $scope.drawGraph("#sms-day-graph", data.sms_day_data, "pink");
                $scope.drawDayGraph("#sms-time-graph", data.sms_time_data, "aqua-front");
            })
    };

    $scope.drawGraph = function drawGraph(elementId, data, colour_name) {
        var colour;
        if (colour_name === "pink")
        {
            colour = "#ec2b8b";
        }
        else {
            colour = "#00b9ad";
        }

        //Width and height
        var w = 800;
        var h = 400;
        var padding = 50;

        var heading = data.heading;
        var dataset = [];
        var now = d3.time.day.utc(new Date);

        var xSize = data.dataset.length;
        for (var x= 0; x<xSize; x++)
        {
            var ySize = data.dataset[x].length;
            var subset = [];
            for (var y=0; y<ySize; y++)
            {
                subset.push ({x: d3.time.day.utc.offset(now, data.dataset[x][y][0]), y: data.dataset[x][y][1]});
            }
            dataset.push(subset);
        }

        // Define axis ranges & scales
        var yExtents = d3.extent(d3.merge(dataset), function (d) { return d.y; });
        var xExtents = d3.extent(d3.merge(dataset), function (d) { return d.x; });

        var xScale = d3.time.scale()
            .domain([xExtents[0], xExtents[1]])
            .range([padding, w - padding * 2]);

	    var yScale = d3.scale.linear()
            .domain([0, yExtents[1]])
	        .range([h - padding, padding]);

        // Create SVG element
	    var svg = d3.select(elementId)
            .append("svg")
            .attr("width", w)
            .attr("height", h)
            .attr("class", "graph")

        // Define lines
        var line = d3.svg.line()
           .x(function(d) { return x(d.x); })
           .y(function(d) { return y(d.y1, d.y2, d.y3); });

        var pathContainers = svg.selectAll('g.line')
            .data(dataset);

        pathContainers.enter().append('g')
            .attr('class', 'line')
            .attr("style", function(d) {
                return "stroke: " + colour;
            });

        pathContainers.selectAll('path')
            .data(function (d) { return [d]; }) // continues the data from the pathContainer
            .enter().append('path')
            .attr('d', d3.svg.line()
                .x(function (d) { return xScale(d.x); })
                .y(function (d) { return yScale(d.y); })
            );

        // add circles
        pathContainers.selectAll('circle')
            .data(function (d) { return d; })
            .enter().append('circle')
            .attr('cx', function (d) { return xScale(d.x); })
            .attr('cy', function (d) { return yScale(d.y); })
            .attr('r', 5);

        // add count on the peak
        pathContainers.selectAll('text')
            .data(function (d) { return d; })
            .enter().append("text")
            .attr("dx", function (d) { return xScale(d.x) - 5; })
            .attr("dy", function (d) { return yScale(d.y) - 10; })
            .attr("font-weight", "normal")
            .text(function(d){ return d.y; })

        //Define X axis
        var xAxis = d3.svg.axis()
            .scale(xScale)
            .orient("bottom")
            .ticks(5)
            .tickFormat(d3.time.format('%a %e'));;

        //Define Y axis
        var yAxis = d3.svg.axis()
            .scale(yScale)
            .orient("left")
            .ticks(5);

        //Add X axis
        svg.append("g")
            .attr("class", "axis")
            .attr("transform", "translate(0," + (h - padding) + ")")
            .call(xAxis);

        //Add Y axis
        svg.append("g")
            .attr("class", "axis")
            .attr("transform", "translate(" + padding + ",0)")
            .call(yAxis);

        // Add title
        svg.append("svg:text")
            .attr("class", "title")
            .attr("x", 20)
            .attr("y", 20)
            .text(heading);
    };

    $scope.drawDayGraph = function drawDayGraph(elementId, data, colourName) {
                var colour;
        if (colourName === "pink")
        {
            colour = "#ec2b8b";
        }
        else {
            colour = "#00b9ad";
        }

        //Width and height
        var w = 800;
        var h = 400;
        var padding = 50;

        var heading = data.heading;
        var dataset = [];
        var now = d3.time.hour.utc(new Date);
        now.setHours(0, 0, 0, 0);
        now.setMinutes(0, 0, 0);

        var xSize = data.dataset.length;
        for (var x= 0; x<xSize; x++)
        {
            var ySize = data.dataset[x].length;
            var subset = [];
            for (var y=0; y<ySize; y++)
            {
                subset.push ({x: d3.time.hour.utc.offset(now, data.dataset[x][y][0]), y: data.dataset[x][y][1]});
            }
            dataset.push(subset);
        }

        // Define axis ranges & scales
        var yExtents = d3.extent(d3.merge(dataset), function (d) { return d.y; });
        var xExtents = d3.extent(d3.merge(dataset), function (d) { return d.x; });

        var xScale = d3.time.scale()
            .domain([xExtents[0], xExtents[1]])
            .range([padding, w - padding * 2]);

	    var yScale = d3.scale.linear()
            .domain([0, yExtents[1]])
	        .range([h - padding, padding]);

        // Create SVG element
	    var svg = d3.select(elementId)
            .append("svg")
            .attr("width", w)
            .attr("height", h)
            .attr("class", "graph")

        // Define lines
        var line = d3.svg.line()
           .x(function(d) { return x(d.x); })
           .y(function(d) { return y(d.y1, d.y2, d.y3); });

        var pathContainers = svg.selectAll('g.line')
            .data(dataset);

        pathContainers.enter().append('g')
            .attr('class', 'line')
            .attr("style", function(d) {
                return "stroke: " + colour;
            });

        pathContainers.selectAll('path')
            .data(function (d) { return [d]; }) // continues the data from the pathContainer
            .enter().append('path')
            .attr('d', d3.svg.line()
                .x(function (d) { return xScale(d.x); })
                .y(function (d) { return yScale(d.y); })
            );

        // add circles
        pathContainers.selectAll('circle')
            .data(function (d) { return d; })
            .enter().append('circle')
            .attr('cx', function (d) { return xScale(d.x); })
            .attr('cy', function (d) { return yScale(d.y); })
            .attr('r', 5);

        // add count on the peak
        pathContainers.selectAll('text')
            .data(function (d) { return d; })
            .enter().append("text")
            .attr("dx", function (d) { return xScale(d.x) - 5; })
            .attr("dy", function (d) { return yScale(d.y) - 10; })
            .attr("font-weight", "normal")
            .text(function(d){ return d.y; })

        //Define X axis
        var xAxis = d3.svg.axis()
            .scale(xScale)
            .orient("bottom")
            .ticks(d3.time.hours, 2)
            .tickFormat(d3.time.format("%H %p"), 2);

        //Define Y axis
        var yAxis = d3.svg.axis()
            .scale(yScale)
            .orient("left")
            .ticks(5);

        //Add X axis
        svg.append("g")
            .attr("class", "axis")
            .attr("transform", "translate(0," + (h - padding) + ")")
            .call(xAxis);

        //Add Y axis
        svg.append("g")
            .attr("class", "axis")
            .attr("transform", "translate(" + padding + ",0)")
            .call(yAxis);

        // Add title
        svg.append("svg:text")
            .attr("class", "title")
            .attr("x", 20)
            .attr("y", 20)
            .text(heading);
    }
});
