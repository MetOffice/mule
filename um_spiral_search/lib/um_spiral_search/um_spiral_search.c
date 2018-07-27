/**********************************************************************/
/* (C) Crown copyright Met Office. All rights reserved.               */
/* For further details please refer to the file LICENCE.txt           */
/* which you should have received as part of this distribution.       */
/* *****************************COPYRIGHT******************************/
/*                                                                    */
/* This file is part of the SHUMlib spiral search library extension   */
/* module for Mule.                                                   */
/*                                                                    */
/* Mule is free software: you can redistribute it and/or modify it    */
/* under the terms of the Modified BSD License, as published by the   */
/* Open Source Initiative.                                            */
/*                                                                    */
/* Mule is distributed in the hope that it will be useful,            */
/* but WITHOUT ANY WARRANTY; without even the implied warranty of     */
/* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the      */
/* Modified BSD License for more details.                             */
/*                                                                    */
/* You should have received a copy of the Modified BSD License        */
/* along with Mule.                                                   */
/* If not, see <http://opensource.org/licenses/BSD-3-Clause>.         */
/* ********************************************************************/

#ifndef NPY_1_7_API_VERSION
#define NPY_1_7_API_VERSION 0x00000007
#endif

#ifndef NPY_NO_DEPRECATED_API
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#endif

#include <Python.h>
#include <numpy/arrayobject.h>
#include <stdbool.h>
#include <stdint.h>
#include "c_shum_spiral_search.h"

#if PY_MAJOR_VERSION >= 3
#define PyInt_FromLong PyLong_FromLong
#define MOD_ERROR_VAL NULL
#define MOD_SUCCESS_VAL(val) val
#define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
#define MOD_DEF(ob, name, doc, methods)               \
  static struct PyModuleDef moduledef = {             \
    PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
  ob = PyModule_Create(&moduledef);
#else
#define MOD_ERROR_VAL
#define MOD_SUCCESS_VAL(val)
#define MOD_INIT(name) PyMODINIT_FUNC init##name(void)
#define MOD_DEF(ob, name, doc, methods)               \
  ob = Py_InitModule3(name, methods, doc);
#endif

MOD_INIT(um_spiral_search);

static PyObject *spiral_search_py(PyObject *self, PyObject *args);

MOD_INIT(um_spiral_search)
{
  PyDoc_STRVAR(um_spiral_search__doc__,
  "This extension module provides access to the SHUMlib spiral search library.\n"
  );

  PyDoc_STRVAR(spiral_search__doc__,
  "Usage:\n"
  "  um_spiral_search.spiral_search( \n"
  "      lsm, index_unres, unres_mask, lats, lons, planet_radius, \n"
  "      cyclic, is_land_field, constrained, constrained_max_dist, \n"
  "      dist_step) \n\n"
  "Args:\n"
  "* lsm                  - land sea mask array (1d, must be \n"
  "                         len(lats)*len(lons))\n"
  "* index_unres          - unresolved point indices (1d)\n"
  "* unres_mask           - mask showing unresolved points (1d, must \n"
  "                         be len(lats)*len(lons))\n"
  "* lats                 - latitudes\n"
  "* lons                 - longitudes\n"
  "* planet_radius        - in metres\n"
  "* cyclic               - True if domain is cyclic E/W\n"
  "* is_land_field        - True if field is a land field\n"
  "* constrained          - True if a distance constraint is applied\n"
  "* constrained_max_dist - distance constraint (in metres)\n"
  "* dist_step            - step coefficient for distance search\n\n"             
  "Returns:\n"
  "  1 Dimensional numpy.ndarray givng the indices which each of the\n"
  "  points in index_unres resolves to.\n"
  );

  static PyMethodDef um_spiral_searchMethods[] = {
    {"spiral_search", spiral_search_py, METH_VARARGS, spiral_search__doc__},
    {NULL, NULL, 0, NULL}
  };

  PyObject *mod;
  MOD_DEF(mod, "um_spiral_search", um_spiral_search__doc__,
          um_spiral_searchMethods);
  if (mod == NULL)
    return MOD_ERROR_VAL;

  import_array();
  return MOD_SUCCESS_VAL(mod);
}

static PyObject *spiral_search_py(PyObject *self, PyObject *args)
{

  // Setup and obtain inputs passed from python
  PyArrayObject *lsm;
  PyArrayObject *index_unres;
  PyArrayObject *unres_mask;
  PyArrayObject *lats;
  PyArrayObject *lons;

  double planet_radius;
  PyObject *cyclic;
  PyObject *is_land_field;
  PyObject *constrained;
  double constrained_max_dist;
  double dist_step;

  // Note the argument descriptors:
  if (!PyArg_ParseTuple(args, "OOOOOdOOOdd",
                        &lsm, &index_unres, &unres_mask, 
                        &lats, &lons, &planet_radius, &cyclic, &is_land_field, 
                        &constrained, &constrained_max_dist, &dist_step)) return NULL;

  // Cast self to void to avoid unused paramter errors
  (void) self;

  bool cyclic_bool = (bool) PyObject_IsTrue(cyclic);
  bool is_land_field_bool = (bool) PyObject_IsTrue(is_land_field);
  bool constrained_bool = (bool) PyObject_IsTrue(constrained);

  // Get phi/lambda dimensions
  npy_intp *dim_lats = PyArray_DIMS(lats);
  npy_intp *dim_lons = PyArray_DIMS(lons);
  npy_intp *dim_mask = PyArray_DIMS(unres_mask);
  npy_intp *dim_unres = PyArray_DIMS(index_unres);
  npy_intp *dim_lsm = PyArray_DIMS(lsm);

  int64_t points_phi = (int64_t) dim_lats[0];
  int64_t points_lambda = (int64_t) dim_lons[0];
  int64_t no_point_unres = (int64_t) dim_unres[0];

  // Check that the arrays are correctly sized
  if ((int64_t) dim_mask[0] != points_phi*points_lambda) {
    PyErr_SetString(PyExc_ValueError,
                    "Mask length not equal to product of lat + lon lengths");
    return NULL;
  }

  if ((int64_t) dim_lsm[0] != points_phi*points_lambda) {
    PyErr_SetString(PyExc_ValueError,
                    "Land/Sea mask length not equal to product of lat + lon lengths");
    return NULL;
  }

  // Get the data from the arrays
  bool *lsm_ptr = (bool *) PyArray_DATA(lsm);
  bool *unres_mask_ptr = (bool *) PyArray_DATA(unres_mask);
  double *lats_ptr = (double *) PyArray_DATA(lats);
  double *lons_ptr = (double *) PyArray_DATA(lons);

  // Create a copy of the unresolved indices (to avoid updating them in place!)
  int64_t index_unres_data[no_point_unres];
  int64_t *index_unres_ptr = (int64_t *) PyArray_DATA(index_unres);
  // The indices passed in will be using 0-based (C) indexing...
  int i;
  for (i = 0; i < no_point_unres; i++)
    {
      index_unres_data[i] = index_unres_ptr[i] + 1;
    }  

  // Setup output array object and dimensions
  PyArrayObject *npy_array_out = NULL;
  npy_intp dims_out[1];

  // Allocate space for return value
  int64_t *indices =
    (int64_t*)calloc((size_t)(no_point_unres), sizeof(int64_t));
  if (indices == NULL) {
    PyErr_SetString(PyExc_ValueError, "Unable to allocate memory for output indices");
    return NULL;
  }
 
  int64_t msg_len = 512;
  char err_msg[msg_len];

  int64_t status;

  status = c_shum_spiral_search_algorithm(lsm_ptr,
                                          index_unres_data,
                                          &no_point_unres,
                                          &points_phi,
                                          &points_lambda,
                                          lats_ptr,
                                          lons_ptr,
                                          &is_land_field_bool,
                                          &constrained_bool,
                                          &constrained_max_dist,
                                          &dist_step,
                                          &cyclic_bool,
                                          unres_mask_ptr,
                                          indices,
                                          &planet_radius,
                                          &err_msg[0],
                                          &msg_len);

  if (status > 0) {
    free(indices);
    PyErr_SetString(PyExc_ValueError, err_msg);
    return NULL;
  }
  if (status < 0) {
    PyErr_WarnEx(PyExc_RuntimeWarning, err_msg, 1);
  }

  // The indices returned will be using 1-based (Fortran) indexing...
  for (i = 0; i < no_point_unres; i++)
    {
      indices[i] = indices[i] - 1;
    }

  // Now form a numpy array object to return to python
  dims_out[0] = no_point_unres;
  npy_array_out=(PyArrayObject *) PyArray_SimpleNewFromData(1, dims_out,
                                                            NPY_INT64,
                                                            indices);
  if (npy_array_out == NULL) {
    free(indices);
    PyErr_SetString(PyExc_ValueError, "Failed to make numpy array");
    return NULL;
  }

  // Give python/numpy ownership of the memory storing the return array
  #if NPY_API_VERSION >= NPY_1_7_API_VERSION
  PyArray_ENABLEFLAGS(npy_array_out, NPY_ARRAY_OWNDATA);
  #else
  npy_array_out->flags = npy_array_out->flags | NPY_OWNDATA;
  #endif

  return (PyObject *)npy_array_out;
}
