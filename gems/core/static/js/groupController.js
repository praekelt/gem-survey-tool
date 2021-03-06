var gems = angular.module('gems');

gems.controller('groupController', function($scope, $http){
    $scope.groupName = $scope.getGroupName();
    $scope.queryStarted = false;
    $scope.numberOfRows = 0;
    $scope.rows = [];
    $scope.columns = [];

    $scope.filteredGroups = [];
    $scope.pagedGroups = [];
    $scope.currentPage = 1;
    $scope.maxSize = 6;
    $scope.buttonText = "Display Results";
    $scope.queryDone = true;
    $scope.showAllResults = false;
    $scope.dispCol = {
        hide: false
    };

    $scope.fetchResults = function fetchResults(){
        $scope.rows = [];
        $scope.queryStarted = true;
        $scope.queryDone = false;
        $scope.buttonText = "Loading Results";
        $scope.showAllResults = false;
        var payload = {};

        if($scope.numberOfRows != null && $scope.numberOfRows > 0){
            payload.limit = $scope.numberOfRows;
        }

        payload.filters = $scope.filters
        $scope.columns = $scope.origColumns.slice();

        if ($scope.createGroup == false && $scope.groupKey != null) {
            var group_contacts;
            $http({url: 'group/contacts', method: 'POST', data: {group_key: $scope.groupKey}})
                .then(function(data) {
                    group_contacts = data.data;
                    $http({
                        url: '/query/',
                        method: 'POST',
                        data: payload
                    })
                    .then(function(data){
                        var results = data.data;
                        var retVal = $scope.processQueryResults(results, $scope.columns, payload.filters);
                        $scope.columns = retVal[0];
                        $scope.rows = retVal[1];

                        if ($scope.queryStarted == true) {
                            $scope.buttonText = "Refresh Results";
                        } else {
                            $scope.buttonText = "Display Results";
                        }

                        for (var i=0; i<results.length; i++) {
                            if (group_contacts.indexOf(results[i].contact) >= 0) {
                                $scope.rows[i].selected = true;
                            }
                        }
                        $scope.queryDone = true;
                        $scope.currentPage = 0;
                        $scope.pagedGroups = $scope.groupToPages($scope.rows);
                    });
                });
        } else {
            $http({
                url: '/query/',
                method: 'POST',
                data: payload
            })
            .then(function(data){
                var results = data.data;
                var retVal = $scope.processQueryResults(results, $scope.columns, payload.filters);
                $scope.columns = retVal[0];
                $scope.rows = retVal[1];

                if ($scope.queryStarted == true) {
                    $scope.buttonText = "Refresh Results";
                } else {
                    $scope.buttonText = "Display Results";
                }
                $scope.queryDone = true;
                $scope.currentPage = 0;
                $scope.pagedGroups = $scope.groupToPages($scope.rows);
            });
        }
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

        $scope.showMessage('Busy', 'Creating Group');
        $http.post('/create_contactgroup/', group, config={timeout: 300000}).
            success(function(status){
                $scope.hideMessage();
                $scope.showAlert('alert-success', 'Success:', status);
            }).
            error(function(data, status){
                $scope.hideMessage();
                $scope.showAlert('alert-warning', 'Failed:', status + ' : ' + data);
            });

        $scope.cancel();
    };

    //need group_key
    $scope.updateGroup = function updateGroup(filters){
        var group = $scope.getGroup(filters);
        group.group_key = $scope.groupKey;

        $http.post('/update_contactgroup/', group).
            success(function(status){
                $scope.showAlert('alert-success', 'Success', status);
            }).
            error(function(status){
                $scope.showAlert('alert-warning', 'Failed', 'Failed to update contact group.'  + '\n\n' + status);
            });

        $scope.cancel();
    };

    ///////PAGING/////
    $scope.groupToPages = function(results){
        var paged = [];
        var temp = results.slice();
        while (temp.length > 0)
        {
            paged.push(temp.splice(0, $scope.itemsPerPage));
        }
        return paged;
    };

    $scope.setPage = function (){
        $scope.currentPage = this.n;
    };

    $scope.cancel = function cancel(){
        $scope.hideCreateContact();
    };

    $scope.$watch('$parent.createGroup', function(newValue, oldValue){
        if(newValue){
            $scope.groupName = $scope.getGroupName();
        }
    });

    $scope.queryValid = function queryValid(){
        return $scope.getQueryValid();
    }

    $scope.toggleShowAllResults = function toggleShowAllResults(){
        $scope.showAllResults = !$scope.showAllResults;

        var retVal = $scope.toggleColumnsAndRows($scope.columns, $scope.rows);
        $scope.columns = retVal[0];
        $scope.rows = retVal[1];
    }
});
