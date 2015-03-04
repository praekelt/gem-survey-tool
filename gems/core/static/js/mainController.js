var gems = angular.module('gems');

gems.controller('mainController', function($scope, $http, $window){
    $scope.showSurveyDataMenu = false;
    $scope.showContactMenu = false;
    $scope.showCreateGroup = false;
    $scope.showContactGroups = false;
    $scope.showExportSurvey = false;
    $scope.showExportSurveyData = false;
    $scope.groupName = '';
    $scope.topQueryWords = '';
    $scope.groupKey = '';

    $scope.filters = [];
    $scope.createGroup = true;

    $scope.toggleSurveyDataMenu = function toggleSurveyDataMenu(){
        $scope.showSurveyDataMenu = !$scope.showSurveyDataMenu;

        if($scope.showSurveyDataMenu == true){
            $scope.showContactMenu = false;
        }
    };

    $scope.toggleContactMenu = function toggleContactMenu(){
        $scope.showContactMenu = !$scope.showContactMenu;

        if($scope.showContactMenu == true){
            $scope.showSurveyDataMenu = false;
        }
    };

    $scope.hideSubMenus = function hideSubMenus(url){
        $scope.showSurveyDataMenu = false;
        $scope.showContactMenu = false;
        $scope.showCreateGroup = false;
        $scope.showContactGroups = false;
        $scope.showExportSurvey = false;
        $scope.showExportSurveyData = false;

        if(typeof(url) != 'undefined'){
            $window.location.href = url;
        }
    };

    $scope.showCreateContact = function showCreateContact(){
        $scope.showContactGroups = false;
        $scope.showCreateGroup = true;
        $scope.showExportSurvey = false;
        $scope.showExportSurveyData = false;
        $scope.createGroup = true;
        $scope.filters = [];
    };

    $scope.hideCreateContact = function hideCreateContact(){
        $scope.showCreateGroup = false;
        $scope.filters = [];
    };

    $scope.showViewContactGroups = function showViewContactGroups(){
        $scope.showContactGroups = true;
        $scope.showCreateGroup = false;
        $scope.showExportSurvey = false;
        $scope.showExportSurveyData = false;
    };

    $scope.hideViewContactGroups = function hideViewContactGroups(){
        $scope.showContactGroups = false;
    };

    $scope.showEditContact = function showEditContact(name, filters, group_key){
        $scope.showContactGroups = false;
        $scope.showCreateGroup = true;
        $scope.createGroup = false;
        if(typeof(filters) === 'string'){
            $scope.filters = JSON.parse(filters);
        } else {
            $scope.filters = filters;
        }
        $scope.groupName = name;
        $scope.groupKey = group_key;
    };

    $scope.showViewExportSurvey = function showViewExportSurvey(){
        $scope.showContactGroups = false;
        $scope.showCreateGroup = false;
        $scope.showExportSurvey = true;
        $scope.showExportSurveyData = false;
    };

    $scope.hideViewExportSurvey = function hideViewExportSurvey(){
        $scope.showExportSurvey = false;
    };

    $scope.showViewExportSurveyData = function showViewExportSurveyData(){
        $scope.showContactGroups = false;
        $scope.showCreateGroup = false;
        $scope.showExportSurvey = false;
        $scope.showExportSurveyData = true;
    };

    $scope.hideViewExportSurveyData = function hideViewExportSurveyData(){
        $scope.showExportSurveyData = false;
    };

    $scope.hideViews = function hideViews(){
        $scope.showContactGroups = false;
        $scope.showCreateGroup = false;
        $scope.showExportSurvey = false;
        $scope.showExportSurveyData = false;
    };

    $scope.getGroupName = function getGroupName(){
        return $scope.groupName;
    };

    $scope.setGroupname = function setGroupName(name){
        return $scope.groupName = name;
    };

    $scope.setQueryWords = function setQueryWords(qw){
        $scope.topQueryWords = qw;
    };

    $scope.getQueryWords = function getQueryWords(){
        return $scope.topQueryWords;
    };
});