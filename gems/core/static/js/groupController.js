var gems = angular.module('gems');

gems.controller('groupController', function($scope, $http){
    $scope.groupName = $scope.getGroupName();
    $scope.fields = [];
    $scope.queryStarted = false;
    $scope.numberOfRows = 0;
    $scope.columns = [];
    $scope.rows = [];

    $scope.fetchResults = function fetchResults(){
        $scope.rows = [];
        $scope.queryStarted = true;
        var payload = {};

        if($scope.numberOfRows != null && $scope.numberOfRows > 0){
            payload.limit = $scope.numberOfRows;
        }

        payload.filters = $scope.filters;

        $http({
            url: '/query/',
            method: 'POST',
            data: payload
            })
            .then(function(data){
                var results = data.data;

                for(var x = 0; x < results.length; ++x){
                    var fields = results[x].fields;
                    var answer = fields['answer'];
                    var row = {
                        selected: false,
                        fields: []
                    };

                    fields.id = results[x].pk;

                    for(var y = 0; y < $scope.columns.length; ++y){
                        var column = $scope.columns[y];

                        if(fields.hasOwnProperty(column.name)){
                            row.fields.push(fields[column.name]);
                        } else if(answer.hasOwnProperty(column.name)){
                            row.fields.push(answer[column.name]);
                        } else {
                            row.fields.push('');
                        }
                    }

                    $scope.rows.push(row);
                }
            })
    };

    $scope.fetchFields = function fetchFields(){
        $http.get('/get_unique_keys/')
            .success(function(data){
                $scope.fields = data;
                $scope.columns = $scope.fields;
            })
    };

    $scope.selectRow = function selectRow(index){
        $scope.rows[index].selected = true;
    };

    $scope.selectFunction = function selectFunction(){
        if($scope.allRowsSelected()){
            // deselect all rows
            for(var x = 0; x < $scope.rows.length; ++x){
                $scope.rows[x].selected = false;
            }
        } else {
            // select all rows
            for(var x = 0; x < $scope.rows.length; ++x){
                $scope.rows[x].selected = true;
            }
        }
    };

    $scope.allRowsSelected = function allRowsSelected(){
        var retVal = true;

        for(var x = 0; x < $scope.rows.length; ++x){
            retVal = retVal && $scope.rows[x].selected;
        }

        return retVal;
    };

    $scope.anyRowsSelected = function anyRowsSelected(){
        var retVal = false;

        for(var x = 0; x < $scope.rows.length; ++x){
            retVal = retVal || $scope.rows[x].selected;
        }

        return retVal;
    };

    $scope.getGroup = function getGroup(filters){
        var group = {
            name: $scope.groupName,
            members: [],
            query_words: $scope.getQueryWords(),
            filters: JSON.stringify( filters )
        };

        var contactIndex = 0;

        for(var x = 0; x < $scope.fields.length; ++x){
            if($scope.fields[x].name === 'contact' ){
                contactIndex = x;
                break;
            }
        }

        for(var x = 0; x < $scope.rows.length; ++x){
            if($scope.rows[x].selected){
                group.members.push($scope.rows[x].fields[contactIndex]);
            }
        }

        return group;
    };

    $scope.saveGroup = function saveGroup(filters){
        var group = $scope.getGroup(filters);

        $http.post('/create_contactgroup/', group).
            success(function(status){
                alert(status);
            }).
            error(function(status){
                alert("Failed to create contact group." + "\n\n" + status);
            });

        $scope.cancel();
    };

    //need group_key
    $scope.updateGroup = function updateGroup(filters){
        var group = $scope.getGroup(filters);
        group.group_key = $scope.groupKey;

        $http.post('/update_contactgroup/', group).
            success(function(status){
                alert(status);
            }).
            error(function(status){
                alert("Failed to update contact group." + "\n\n" + status);
            });

        $scope.cancel();
    };

    $scope.cancel = function cancel(){
        $scope.hideCreateContact();
    };

    $scope.fetchFields();
});